# Kong Gateway Examples

Comprehensive examples for managing Kong Gateway with the ops CLI. Each section includes
context, prerequisites, step-by-step commands, expected output, and troubleshooting tips.

---

## Getting Started

### Checking Kong Connectivity

**Context**: Before running any Kong commands, verify that the CLI can connect to your
Kong Admin API.

**Prerequisites**:

- Kong Gateway running and accessible
- Admin API URL configured (default: `http://localhost:8001`)

**Steps**:

```bash
# Check Kong status
ops kong status
```

**Expected Output**:

```text
Kong Gateway Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Node:        kong-node-1
Version:     3.4.0
Edition:     Enterprise
Database:    PostgreSQL (connected)
Uptime:      3d 14h 22m
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Connections: 1,247 active
Requests:    45,892,103 total
Memory:      256 MB / 1024 MB
```

**Troubleshooting**:

| Issue                 | Solution                                                    |
| --------------------- | ----------------------------------------------------------- |
| Connection refused    | Verify Kong is running: `curl http://localhost:8001/status` |
| Timeout               | Check firewall rules and network connectivity               |
| Authentication failed | Verify API key or mTLS certificates in config               |

### Viewing Kong Configuration

```bash
# Get detailed Kong information
ops kong info

# Output as JSON for scripting
ops kong info --output json
```

---

## Basic API Setup

### Creating Your First API

**Context**: Expose a backend service through Kong Gateway with a public route.

**Prerequisites**:

- Kong Gateway running
- Backend service accessible from Kong (e.g., `backend.internal:8080`)

**Step 1: Create a Service**

A service represents your upstream backend API.

```bash
ops kong services create \
  --name my-api \
  --host backend.internal \
  --port 8080 \
  --protocol http \
  --path /api/v1 \
  --tag production
```

**Expected Output**:

```text
Service created successfully!

Service: my-api
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ID:          8f3c9b2a-1234-5678-abcd-ef0123456789
Name:        my-api
Host:        backend.internal
Port:        8080
Protocol:    http
Path:        /api/v1
Tags:        production
Enabled:     true
```

**Step 2: Create a Route**

A route defines how clients access the service.

```bash
ops kong routes create \
  --name my-api-route \
  --service my-api \
  --path /api \
  --method GET \
  --method POST \
  --host api.example.com \
  --strip-path
```

**Step 3: Verify the Setup**

```bash
# List all services
ops kong services list

# View routes for the service
ops kong services routes my-api

# Test the proxy (from outside Kong)
curl -i http://api.example.com/api/users
```

**Troubleshooting**:

| Issue             | Solution                                                       |
| ----------------- | -------------------------------------------------------------- |
| 404 Not Found     | Verify route path and host match your request                  |
| 502 Bad Gateway   | Check service host/port are reachable from Kong                |
| Service not found | Ensure service name exists with `ops kong services get my-api` |

---

## Authentication Examples

### API Key Authentication

**Context**: Protect your API with API keys. Consumers must provide a valid key to access.

**Prerequisites**:

- Service and route already created

**Step 1: Enable Key-Auth Plugin**

```bash
ops kong security key-auth enable \
  --service my-api \
  --hide-credentials  # Don't forward the key to upstream
```

**Step 2: Create a Consumer**

```bash
ops kong consumers create \
  --username mobile-app \
  --custom-id app-12345 \
  --tag mobile
```

**Step 3: Create an API Key**

```bash
ops kong security key-auth create-key mobile-app \
  --key "my-secret-api-key-123"
```

**Expected Output**:

```text
API Key created successfully!

Consumer:    mobile-app
Key:         my-secret-api-key-123
ID:          abc123-key-id
```

**Step 4: Test Authentication**

```bash
# Without key - should fail
curl -i http://api.example.com/api/users
# Returns: 401 Unauthorized

# With key - should succeed
curl -i -H "apikey: $API_KEY" http://api.example.com/api/users
# Returns: 200 OK
```

**List and Manage Keys**:

```bash
# List all keys for a consumer
ops kong security key-auth list-keys mobile-app

# Revoke a key
ops kong security key-auth revoke-key mobile-app abc123-key-id
```

### JWT Authentication

**Context**: Use JSON Web Tokens for stateless authentication. Ideal for microservices
and single-page applications.

**Step 1: Enable JWT Plugin**

```bash
ops kong security jwt enable \
  --service my-api \
  --claim exp \
  --claim nbf
```

**Step 2: Create JWT Credentials**

```bash
# For HS256 (symmetric)
ops kong security jwt add-credential mobile-app \
  --key "jwt-key-identifier" \
  --algorithm HS256 \
  --secret "my-super-secret-jwt-key"

# For RS256 (asymmetric)
ops kong security jwt add-credential mobile-app \
  --key "jwt-key-identifier" \
  --algorithm RS256 \
  --rsa-public-key @public-key.pem
```

**Step 3: Generate and Use Token**

Example JWT payload:

```json
{
  "iss": "jwt-key-identifier",
  "exp": 1735689600,
  "nbf": 1704153600,
  "sub": "user123"
}
```

```bash
# Use the token
curl -i -H "Authorization: Bearer $JWT_TOKEN" \
  http://api.example.com/api/users
```

### OAuth2 Authentication

**Context**: Enable OAuth2 flows for third-party applications.

```bash
# Enable OAuth2 plugin
ops kong security oauth2 enable \
  --service my-api \
  --scopes read \
  --scopes write \
  --mandatory-scope \
  --enable-authorization-code

# Create OAuth2 application
ops kong security oauth2 create-app mobile-app \
  --name "Mobile Application" \
  --client-id "mobile-client-id" \
  --client-secret "mobile-client-secret" \
  --redirect-uri "https://app.example.com/callback"
```

### Access Control Lists (ACL)

**Context**: Group-based access control for fine-grained permissions.

```bash
# Enable ACL plugin (allow only premium-users group)
ops kong security acl enable \
  --service my-api \
  --allow premium-users \
  --allow admin

# Add consumer to a group
ops kong security acl add-group mobile-app premium-users

# List groups for a consumer
ops kong security acl list-groups mobile-app

# Remove from group
ops kong security acl remove-group mobile-app premium-users
```

---

## Traffic Control Examples

### Rate Limiting

**Context**: Protect your API from abuse by limiting request rates.

**Basic Rate Limiting**:

```bash
# Simple rate limit: 100 requests per minute
ops kong traffic rate-limit enable \
  --service my-api \
  --minute 100
```

**Advanced Rate Limiting**:

```bash
# Multiple time windows with policy
ops kong traffic rate-limit enable \
  --service my-api \
  --second 10 \
  --minute 100 \
  --hour 1000 \
  --policy local \
  --limit-by consumer
```

**Expected Response Headers**:

```text
X-RateLimit-Limit-Minute: 100
X-RateLimit-Remaining-Minute: 95
```

**Consumer-Specific Rate Limits (Tiered Pricing)**:

```bash
# Free tier consumer: 60 requests/minute
ops kong plugins enable rate-limiting \
  --consumer free-user \
  --service my-api \
  --config minute=60

# Pro tier consumer: 1000 requests/minute
ops kong plugins enable rate-limiting \
  --consumer pro-user \
  --service my-api \
  --config minute=1000

# Enterprise tier consumer: 10000 requests/minute
ops kong plugins enable rate-limiting \
  --consumer enterprise-user \
  --service my-api \
  --config minute=10000
```

**Check and Disable Rate Limiting**:

```bash
# View current rate limit config
ops kong traffic rate-limit get --service my-api

# Disable rate limiting
ops kong traffic rate-limit disable --service my-api --force
```

### Request Size Limiting

**Context**: Prevent large payloads from overwhelming your backend.

```bash
# Limit request body to 1MB
ops kong traffic request-size enable \
  --service my-api \
  --size 1048576

# Check configuration
ops kong traffic request-size get --service my-api
```

### Request/Response Transformation

**Context**: Modify requests and responses without changing your backend code.

**Request Transformation**:

```bash
# Add headers to all requests
ops kong traffic request-transformer enable \
  --service my-api \
  --add-header "X-Custom-Header:custom-value" \
  --add-header "X-Request-ID:$(uuid)"

# Remove sensitive headers
ops kong traffic request-transformer enable \
  --service my-api \
  --remove-header "X-Internal-Token"

# Rename headers
ops kong traffic request-transformer enable \
  --service my-api \
  --rename-header "X-Old-Name:X-New-Name"
```

**Response Transformation**:

```bash
# Add CORS and security headers to responses
ops kong traffic response-transformer enable \
  --service my-api \
  --add-header "X-Frame-Options:DENY" \
  --add-header "X-Content-Type-Options:nosniff"
```

---

## Load Balancing Examples

### Setting Up an Upstream with Multiple Targets

**Context**: Distribute traffic across multiple backend servers for high availability.

**Step 1: Create the Upstream**

```bash
ops kong upstreams create payment-cluster \
  --algorithm round-robin \
  --slots 10000
```

**Step 2: Add Targets (Backend Servers)**

```bash
# Add three backend servers
ops kong upstreams targets add payment-cluster \
  --target 192.168.1.10:8080 \
  --weight 100

ops kong upstreams targets add payment-cluster \
  --target 192.168.1.11:8080 \
  --weight 100

ops kong upstreams targets add payment-cluster \
  --target 192.168.1.12:8080 \
  --weight 50  # Lower weight = fewer requests
```

**Step 3: Point Service to Upstream**

```bash
ops kong services update payment-api --host payment-cluster
```

**Step 4: Verify**

```bash
# List targets
ops kong upstreams targets list payment-cluster

# Check health
ops kong upstreams health payment-cluster
```

**Expected Output**:

```text
Upstream Health: payment-cluster
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Overall:         HEALTHY

Targets:
  192.168.1.10:8080   weight: 100   HEALTHY
  192.168.1.11:8080   weight: 100   HEALTHY
  192.168.1.12:8080   weight: 50    HEALTHY
```

### Configuring Health Checks

**Context**: Automatically detect and remove unhealthy backends.

```bash
# Configure active health checks
ops kong observability health set payment-cluster \
  --active-type http \
  --active-http-path /health \
  --active-interval-healthy 10 \
  --active-interval-unhealthy 5 \
  --active-successes-healthy 2 \
  --active-failures-unhealthy 3

# Configure passive health checks (circuit breaker)
ops kong observability health set payment-cluster \
  --passive-type http \
  --passive-successes-healthy 5 \
  --passive-failures-unhealthy 3 \
  --passive-http-statuses-healthy 200,201,204 \
  --passive-http-statuses-unhealthy 500,502,503
```

### Blue-Green Deployment

**Context**: Deploy new versions with zero downtime.

**Step 1: Set Up Two Target Groups**

```bash
# Blue (current production)
ops kong upstreams targets add api-cluster --target blue-v1.internal:8080 --weight 100

# Green (new version, initially weight 0)
ops kong upstreams targets add api-cluster --target green-v2.internal:8080 --weight 0
```

**Step 2: Gradually Shift Traffic**

```bash
# Start canary: 10% to green
ops kong upstreams targets update api-cluster blue-target-id --weight 90
ops kong upstreams targets update api-cluster green-target-id --weight 10

# If healthy, increase to 50%
ops kong upstreams targets update api-cluster blue-target-id --weight 50
ops kong upstreams targets update api-cluster green-target-id --weight 50

# Complete cutover
ops kong upstreams targets update api-cluster blue-target-id --weight 0
ops kong upstreams targets update api-cluster green-target-id --weight 100
```

**Step 3: Rollback if Needed**

```bash
# Quickly roll back to blue
ops kong upstreams targets update api-cluster blue-target-id --weight 100
ops kong upstreams targets update api-cluster green-target-id --weight 0
```

---

## Observability Examples

### Prometheus Metrics

**Context**: Export metrics for monitoring with Prometheus and Grafana.

**Enable Prometheus Plugin**:

```bash
ops kong observability metrics prometheus enable \
  --per-consumer \
  --status-code-metrics \
  --latency-metrics
```

**Scrape Configuration** (prometheus.yml):

```yaml
scrape_configs:
  - job_name: "kong"
    static_configs:
      - targets: ["kong:8001"]
    metrics_path: /metrics
```

**Example PromQL Queries**:

```promql
# Request rate by service
rate(kong_http_requests_total{service="my-api"}[5m])

# 95th percentile latency
histogram_quantile(0.95, rate(kong_request_latency_ms_bucket[5m]))

# Error rate
rate(kong_http_requests_total{code=~"5.."}[5m]) / rate(kong_http_requests_total[5m])
```

### HTTP Logging

**Context**: Send access logs to a centralized logging system.

```bash
# Enable HTTP logging
ops kong observability logs http enable \
  --service my-api \
  --http-endpoint "https://logs.example.com/kong" \
  --method POST \
  --content-type "application/json"
```

### File Logging

```bash
# Enable file logging
ops kong observability logs file enable \
  --service my-api \
  --path /var/log/kong/access.log \
  --reopen
```

### Distributed Tracing with OpenTelemetry

**Context**: Trace requests across microservices for debugging.

```bash
ops kong observability tracing opentelemetry enable \
  --endpoint "http://otel-collector:4318/v1/traces" \
  --header "Authorization:Bearer token123" \
  --resource-attribute "service.name=kong-gateway" \
  --resource-attribute "deployment.environment=production"
```

---

## Enterprise Features

### Workspace Management

**Context**: Isolate configurations for different teams or environments.

```bash
# Create workspaces for different environments
ops kong enterprise workspaces create development --comment "Development environment"
ops kong enterprise workspaces create staging --comment "Staging environment"
ops kong enterprise workspaces create production --comment "Production environment"

# Switch to a workspace
ops kong enterprise workspaces use production

# Check current workspace
ops kong enterprise workspaces current

# All subsequent commands operate in the production workspace
ops kong services list  # Lists only production services
```

### RBAC Configuration

**Context**: Control who can access what in Kong.

```bash
# Create a role for API developers
ops kong enterprise rbac roles create api-developer \
  --comment "Can manage services and routes"

# Add permissions
ops kong enterprise rbac roles add-permission api-developer \
  --endpoint "/services/*" \
  --actions read,create,update

ops kong enterprise rbac roles add-permission api-developer \
  --endpoint "/routes/*" \
  --actions read,create,update

# Create an admin user
ops kong enterprise rbac users create john.doe \
  --email john@example.com \
  --role api-developer

# Assign additional roles
ops kong enterprise rbac users assign-role john.doe super-admin
```

### Vault Integration

**Context**: Store secrets securely instead of in Kong configuration.

```bash
# Configure HashiCorp Vault
ops kong enterprise vaults configure hcv \
  --name "prod-vault" \
  --host vault.internal \
  --port 8200 \
  --mount secret \
  --kv-version 2

# Reference secrets in plugin configuration
ops kong plugins enable key-auth \
  --service my-api \
  --config key_names={vault://prod-vault/api-config/key-header}
```

---

## Declarative Configuration

### Exporting Current State

**Context**: Capture your Kong configuration as code for version control.

```bash
# Export full configuration
ops kong config export kong-state.yaml

# Export specific resources only
ops kong config export services-only.yaml --only services,routes

# Export with credentials (use carefully!)
ops kong config export full-backup.yaml --include-credentials
```

### Validating Configuration

```bash
# Validate before applying
ops kong config validate kong-state.yaml
```

**Expected Output (Valid)**:

```text
Validation Results: kong-state.yaml
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Format Version:  3.0
Services:        3
Routes:          8
Consumers:       15
Upstreams:       2
Plugins:         12
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Status:          VALID
```

### Comparing Changes

```bash
# See what would change
ops kong config diff kong-state.yaml
```

**Expected Output**:

```text
Configuration Diff: kong-state.yaml vs Current State
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Services:
  + new-api (new)
  ~ my-api (modified)
      - port: 8080 -> 8443
  - legacy-api (removed)

Summary: 1 addition, 1 modification, 1 removal
```

### Applying Configuration

```bash
# Dry run first
ops kong config apply kong-state.yaml --dry-run

# Apply with confirmation
ops kong config apply kong-state.yaml --confirm

# Apply without confirmation (CI/CD)
ops kong config apply kong-state.yaml --no-confirm
```

### CI/CD Integration Example

```yaml
# .github/workflows/kong-deploy.yml
name: Deploy Kong Config

on:
  push:
    branches: [main]
    paths: ["kong/**"]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Validate Kong config
        run: ops kong config validate kong/production.yaml

      - name: Show diff
        run: ops kong config diff kong/production.yaml

      - name: Apply config
        run: ops kong config apply kong/production.yaml --no-confirm
        env:
          OPS_KONG_BASE_URL: ${{ secrets.KONG_ADMIN_URL }}
          OPS_KONG_API_KEY: ${{ secrets.KONG_ADMIN_TOKEN }}
```

---

## Konnect Integration

### Checking Sync Status

**Context**: View drift between your Gateway (data plane) and Konnect (control plane).

**Prerequisites**:

- Konnect configured in your ops configuration
- Gateway and Konnect both accessible

**View Sync Status**:

```bash
$ ops kong sync status

Sync Status Report
==================================================

Entity Sync Summary
┌─────────────┬───────┬──────────────┬──────────────┬────────┬────────────┐
│ Entity Type │ Total │ Gateway Only │ Konnect Only │ Synced │ With Drift │
├─────────────┼───────┼──────────────┼──────────────┼────────┼────────────┤
│ Services    │     5 │            1 │            - │      3 │          1 │
│ Routes      │     8 │            2 │            - │      6 │          - │
│ Consumers   │     3 │            - │            - │      3 │          - │
│ Plugins     │     4 │            - │            - │      4 │          - │
│ Upstreams   │     2 │            - │            - │      2 │          - │
├─────────────┼───────┼──────────────┼──────────────┼────────┼────────────┤
│ Total       │    22 │            3 │            - │     18 │          1 │
└─────────────┴───────┴──────────────┴──────────────┴────────┴────────────┘

Entities with Configuration Drift:
  Services:
    - payment-api: host, port

Entities only in Gateway (not in Konnect):
  Services:
    - new-api-service
  Routes:
    - new-api-route
    - test-route
```

**Filter by Entity Type**:

```bash
# Check only services
ops kong sync status --type services

# Check only routes
ops kong sync status --type routes
```

### Syncing Gateway to Konnect

**Context**: Push Gateway configuration to Konnect to bring them in sync.

**Preview Changes (Dry Run)**:

```bash
$ ops kong sync push --dry-run

Sync Preview (dry run)

Services:
  Would create: new-api-service
  Would update: payment-api
    Drift fields: host, port

Routes:
  Would create: new-api-route
  Would create: test-route

Summary:
  Would create: 3 entity(s)
  Would update: 1 entity(s)
```

**Push Changes**:

```bash
$ ops kong sync push --force

Pushing Gateway -> Konnect

Services:
  Created: new-api-service
  Updated: payment-api

Routes:
  Created: new-api-route
  Created: test-route

Summary:
  Created: 3 entity(s)
  Updated: 1 entity(s)
  Errors: 0
✓ Sync complete
```

**Push Specific Entity Types**:

```bash
# Push only services
ops kong sync push --type services --force

# Push only routes
ops kong sync push --type routes --force

# Push upstreams with targets
ops kong sync push --type upstreams --include-targets --force
```

### Pulling from Konnect to Gateway

**Context**: Pull configuration from Konnect to Gateway. Useful for:

- Setting up a new Gateway instance from Konnect configuration
- Recovering Gateway configuration after data loss
- Synchronizing configuration across multiple environments

**Preview Pull**:

```bash
$ ops kong sync pull --dry-run

Sync Preview (dry run)

Services:
  Would create: konnect-only-service
  Would create: production-api

Routes:
  Would create: api-route

Summary:
  Would create: 3 entity(s)
```

**Pull Entities from Konnect**:

```bash
$ ops kong sync pull --force

Pulling Konnect -> Gateway

Services:
  Created: konnect-only-service
  Created: production-api

Routes:
  Created: api-route

Summary:
  Created: 3 entity(s)
✓ Sync complete
```

**Pull with Drift Sync**:

```bash
# Also update entities that exist in both but have different configurations
$ ops kong sync pull --with-drift --force

Pulling Konnect -> Gateway

Services:
  Created: new-service
  Updated: existing-service
    Drift fields: host, port

Summary:
  Created: 1 entity(s)
  Updated: 1 entity(s)
✓ Sync complete
```

**Pull Specific Entity Types**:

```bash
# Pull only services
ops kong sync pull --type services --force

# Pull only upstreams with their targets
ops kong sync pull --type upstreams --include-targets --force
```

### Testing with Gateway Only

**Context**: Use `--data-plane-only` to skip Konnect sync during testing or local development.

**Create Service in Gateway Only**:

```bash
$ ops kong services create --name test-svc --host test.local --data-plane-only

Service created successfully

Service: test-svc
┌──────────┬────────────┐
│ Name     │ test-svc   │
│ Host     │ test.local │
│ Port     │ 80         │
│ Protocol │ http       │
└──────────┴────────────┘
Konnect sync skipped (--data-plane-only)
```

**Update Without Konnect Sync**:

```bash
# Update service without syncing to Konnect
ops kong services update test-svc --port 8080 --data-plane-only

# Delete from Gateway only
ops kong services delete test-svc --data-plane-only
```

**Later, Sync to Konnect**:

```bash
# Push all Gateway changes to Konnect
ops kong sync push --force

# Or push only services
ops kong sync push --type services --force
```

### Handling Konnect Failures

**Context**: When Konnect sync fails, Gateway operations still succeed. The system uses
Gateway-first with Konnect best-effort.

**Example Output with Konnect Failure**:

```bash
$ ops kong services create --name my-api --host api.local

Service created successfully

Service: my-api
┌──────────┬───────────┐
│ Name     │ my-api    │
│ Host     │ api.local │
│ Port     │ 80        │
└──────────┴───────────┘
⚠ Konnect sync failed: Connection timeout
  Run 'ops kong sync push' to retry
```

**Retry Failed Syncs**:

```bash
# Check which entities need syncing
ops kong sync status

# Push any out-of-sync entities
ops kong sync push --force
```

**Troubleshooting**:

| Issue                   | Solution                                                |
| ----------------------- | ------------------------------------------------------- |
| Konnect not configured  | Add Konnect config to `~/.config/ops/config.yaml`       |
| Connection timeout      | Check network connectivity to Konnect API               |
| Authentication failed   | Verify `KONNECT_API_KEY` environment variable           |
| Control plane not found | Check `default_control_plane` in config matches Konnect |

---

## Troubleshooting Reference

### Common Issues

| Issue                  | Symptoms                | Solution                                                    |
| ---------------------- | ----------------------- | ----------------------------------------------------------- |
| Service unreachable    | 502 Bad Gateway         | Check service host/port, verify DNS resolution from Kong    |
| Route not matching     | 404 Not Found           | Verify path, host, and methods match your request           |
| Authentication failing | 401/403 errors          | Check credentials, verify plugin is enabled correctly       |
| Rate limit hit         | 429 Too Many Requests   | Review rate limit config, consider higher limits            |
| DB-less write error    | Operation not permitted | Use `ops kong config apply` instead of direct modifications |

### Debug Mode

```bash
# Enable verbose output
ops kong --verbose services list

# Output as JSON for debugging
ops kong services get my-api --output json

# Check specific entity
ops kong plugins list --service my-api --output json
```

### Verifying Plugin Configuration

```bash
# List all plugins on a service
ops kong plugins list --service my-api

# Get plugin details
ops kong plugins get <plugin-id>

# View plugin schema for available options
ops kong plugins schema rate-limiting
```
