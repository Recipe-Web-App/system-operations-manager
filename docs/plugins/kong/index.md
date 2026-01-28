# Kong Gateway Plugin

Comprehensive integration with Kong Gateway for API management, traffic control,
security, and observability through the Admin API.

## Overview

The Kong plugin provides full integration with Kong Gateway's Admin API, enabling:

- **API Management**: Create and manage services, routes, consumers, and upstreams
- **Traffic Control**: Rate limiting, request/response transformation, circuit breakers
- **Security**: Authentication (key-auth, JWT, OAuth2), ACLs, IP restrictions, mTLS
- **Observability**: Logging, Prometheus metrics, health checks, distributed tracing
- **Declarative Config**: Export, validate, and apply Kong configuration as code
- **Konnect Integration**: Dual-write to both Gateway (data plane) and Konnect (control plane)

### Supported Kong Editions

| Edition         | Support Level                                             |
| --------------- | --------------------------------------------------------- |
| Kong OSS        | Full support for all open-source features                 |
| Kong Enterprise | Extended support for Workspaces, RBAC, Vaults, Dev Portal |

### Deployment Modes

| Mode      | Description                              | Write Operations                                 |
| --------- | ---------------------------------------- | ------------------------------------------------ |
| DB-backed | Traditional PostgreSQL/Cassandra backend | Full CRUD via Admin API                          |
| DB-less   | Declarative configuration via YAML       | Read-only Admin API, use `ops kong config apply` |

## Kong Gateway Concepts

Before using the plugin, understanding Kong's core entities is helpful:

### Services

A **Service** represents an upstream API or microservice. It defines where Kong should proxy requests.

```text
Service: payment-api
  ├── host: payment.internal.example.com
  ├── port: 8080
  ├── protocol: http
  └── path: /api/v1
```

### Routes

A **Route** defines rules for matching client requests to Services. Routes specify paths, hosts, methods, and headers.

```text
Route: payment-route
  ├── paths: ["/payments", "/transactions"]
  ├── methods: ["GET", "POST"]
  ├── hosts: ["api.example.com"]
  └── service: payment-api
```

### Consumers

A **Consumer** represents a user or application consuming your APIs. Consumers can have credentials
and be assigned to groups for access control.

```text
Consumer: mobile-app
  ├── username: mobile-app
  ├── custom_id: app-12345
  └── credentials:
      ├── key-auth: [api-key-1, api-key-2]
      └── jwt: [jwt-credential-1]
```

### Upstreams & Targets

An **Upstream** represents a virtual hostname for load balancing across multiple **Targets** (backend servers).

```text
Upstream: payment-cluster
  ├── algorithm: round-robin
  ├── healthchecks: active + passive
  └── targets:
      ├── 192.168.1.10:8080 (weight: 100)
      ├── 192.168.1.11:8080 (weight: 100)
      └── 192.168.1.12:8080 (weight: 50)
```

### Plugins

**Plugins** add functionality to Kong and can be applied globally, per-service, per-route, or per-consumer.

```text
Plugin: rate-limiting
  ├── scope: service (payment-api)
  ├── config:
  │   ├── minute: 100
  │   ├── hour: 5000
  │   └── policy: local
  └── enabled: true
```

---

## Installation & Configuration

### Enabling the Plugin

Add `kong` to your enabled plugins in `~/.config/ops/config.yaml`:

```yaml
plugins:
  enabled:
    - core
    - kong
```

### Configuration Schema

```yaml
plugins:
  kong:
    # Connection settings
    connection:
      base_url: "http://localhost:8001" # Kong Admin API URL
      timeout: 30 # Request timeout (seconds)
      verify_ssl: true # Verify TLS certificates
      retries: 3 # Retry attempts on failure

    # Authentication (choose one method)
    auth:
      type: "none" # Options: none, api_key, mtls

      # For API key authentication:
      # type: "api_key"
      # api_key: "your-kong-admin-api-key"
      # header_name: "Kong-Admin-Token"  # Default header

      # For mTLS authentication:
      # type: "mtls"
      # cert_path: "/path/to/client.crt"
      # key_path: "/path/to/client.key"
      # ca_path: "/path/to/ca.crt"  # Optional CA bundle

    # Output settings
    output_format: "table" # Options: table, json, yaml
    default_workspace: "default" # Enterprise: default workspace

    # Enterprise settings (auto-detected)
    enterprise:
      enabled: false # Auto-detected based on available endpoints
```

### Environment Variable Overrides

| Variable             | Description                              |
| -------------------- | ---------------------------------------- |
| `OPS_KONG_BASE_URL`  | Override Admin API URL                   |
| `OPS_KONG_API_KEY`   | Override API key                         |
| `OPS_KONG_AUTH_TYPE` | Override auth type (none, api_key, mtls) |
| `OPS_KONG_WORKSPACE` | Override default workspace               |
| `OPS_KONG_OUTPUT`    | Override output format                   |

### Authentication Methods

#### No Authentication (Development/Local)

```yaml
auth:
  type: "none"
```

Use when Admin API is accessible without authentication (localhost, internal network).

#### API Key / Admin Token

```yaml
auth:
  type: "api_key"
  api_key: "${KONG_ADMIN_TOKEN}"
  header_name: "Kong-Admin-Token"
```

For Kong instances secured with RBAC or Admin API authentication.

#### Mutual TLS (mTLS)

```yaml
auth:
  type: "mtls"
  cert_path: "/etc/kong/admin-client.crt"
  key_path: "/etc/kong/admin-client.key"
  ca_path: "/etc/kong/ca-bundle.crt"
```

For production environments with certificate-based authentication.

### Konnect Integration

Connect to Kong Konnect for centralized control plane management. When configured,
write operations (create, update, delete) sync to both Gateway and Konnect.

#### Konnect Configuration

```yaml
plugins:
  kong:
    # ... existing connection settings ...

    # Konnect Control Plane settings
    konnect:
      api_key: "${KONNECT_API_KEY}"
      default_control_plane: "my-control-plane"
      region: "us" # Options: us, eu, au
```

#### Konnect Environment Variables

| Variable                | Description                      |
| ----------------------- | -------------------------------- |
| `KONNECT_API_KEY`       | Konnect API authentication token |
| `KONNECT_CONTROL_PLANE` | Default control plane name       |
| `KONNECT_REGION`        | Konnect region (us, eu, au)      |

#### Dual-Write Behavior

When Konnect is configured:

- **Create/Update/Delete**: Writes to Gateway first, then syncs to Konnect
- **Error Handling**: Gateway-first with Konnect best-effort (no rollback on Konnect failure)
- **Graceful Degradation**: Works when Konnect is unavailable

Use `--data-plane-only` (or `--gateway-only`) to skip Konnect sync:

```bash
ops kong services create --name test-svc --host test.local --data-plane-only
```

---

## CLI Command Reference

### Status & Information

#### `ops kong status`

Display Kong node health and connectivity status.

```bash
ops kong status
```

**Output:**

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

**Options:**

| Option      | Description                     |
| ----------- | ------------------------------- |
| `--json`    | Output as JSON                  |
| `--verbose` | Include additional node details |

#### `ops kong info`

Display detailed Kong configuration and enabled features.

```bash
ops kong info
```

**Output:**

```text
Kong Configuration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Admin API:    http://localhost:8001
Proxy:        http://localhost:8000
Database:     postgres
Cluster:      hybrid (control plane)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Plugins:      32 available, 8 enabled
Services:     15
Routes:       42
Consumers:    128
Upstreams:    6
```

---

### Service Commands

Manage Kong services (upstream API definitions).

#### `ops kong services list`

List all registered services.

```bash
ops kong services list
ops kong services list --tag production
ops kong services list --output json
```

**Options:**

| Option            | Description                       |
| ----------------- | --------------------------------- |
| `--tag TAG`       | Filter by tag                     |
| `--output FORMAT` | Output format (table, json, yaml) |
| `--limit N`       | Limit results                     |
| `--offset N`      | Pagination offset                 |

#### `ops kong services get <name-or-id>`

Get detailed information about a service.

```bash
ops kong services get payment-api
ops kong services get 8f3c9b2a-1234-5678-abcd-ef0123456789
```

#### `ops kong services create`

Create a new service.

```bash
ops kong services create \
  --name payment-api \
  --host payment.internal.example.com \
  --port 8080 \
  --protocol http \
  --path /api/v1 \
  --tag production \
  --tag payments
```

**Options:**

| Option                 | Description                                        | Default |
| ---------------------- | -------------------------------------------------- | ------- |
| `--name`               | Service name (required)                            | -       |
| `--host`               | Upstream host (required)                           | -       |
| `--port`               | Upstream port                                      | 80      |
| `--protocol`           | Protocol (http, https, grpc, grpcs, tcp, udp, tls) | http    |
| `--path`               | Path prefix                                        | /       |
| `--retries`            | Number of retries                                  | 5       |
| `--connect-timeout`    | Connection timeout (ms)                            | 60000   |
| `--read-timeout`       | Read timeout (ms)                                  | 60000   |
| `--write-timeout`      | Write timeout (ms)                                 | 60000   |
| `--tag`                | Tag (repeatable)                                   | -       |
| `--enabled/--disabled` | Enable or disable service                          | enabled |
| `--data-plane-only`    | Write to Gateway only, skip Konnect sync           | false   |
| `--gateway-only`       | Alias for `--data-plane-only`                      | false   |

#### `ops kong services update <name-or-id>`

Update an existing service.

```bash
ops kong services update payment-api --port 8443 --protocol https
ops kong services update payment-api --retries 10 --tag updated
```

#### `ops kong services delete <name-or-id>`

Delete a service.

```bash
ops kong services delete payment-api
ops kong services delete payment-api --force  # Skip confirmation
```

> **Note:** The `--data-plane-only` (or `--gateway-only`) option is available for `create`, `update`,
> and `delete` operations. This flag skips Konnect sync when you want to make changes only to the
> Gateway.

#### `ops kong services routes <name-or-id>`

List routes associated with a service.

```bash
ops kong services routes payment-api
```

---

### Route Commands

Manage Kong routes (request matching rules).

#### `ops kong routes list`

List all routes.

```bash
ops kong routes list
ops kong routes list --service payment-api
ops kong routes list --tag public-api
```

**Options:**

| Option            | Description       |
| ----------------- | ----------------- |
| `--service NAME`  | Filter by service |
| `--tag TAG`       | Filter by tag     |
| `--output FORMAT` | Output format     |

#### `ops kong routes get <name-or-id>`

Get route details.

```bash
ops kong routes get payment-route
```

#### `ops kong routes create`

Create a new route.

```bash
ops kong routes create \
  --name payment-route \
  --service payment-api \
  --path /payments \
  --path /transactions \
  --method GET \
  --method POST \
  --host api.example.com \
  --strip-path \
  --preserve-host
```

**Options:**

| Option                               | Description                         | Default        |
| ------------------------------------ | ----------------------------------- | -------------- |
| `--name`                             | Route name                          | auto-generated |
| `--service`                          | Associated service (required)       | -              |
| `--path`                             | Path pattern (repeatable)           | -              |
| `--method`                           | HTTP method (repeatable)            | all methods    |
| `--host`                             | Hostname (repeatable)               | -              |
| `--header`                           | Header match (format: `name:value`) | -              |
| `--protocol`                         | Protocol (http, https, grpc, grpcs) | http, https    |
| `--strip-path/--no-strip-path`       | Strip matched path                  | strip          |
| `--preserve-host/--no-preserve-host` | Preserve original Host header       | no-preserve    |
| `--regex-priority`                   | Regex route priority                | 0              |
| `--tag`                              | Tag (repeatable)                    | -              |

#### `ops kong routes update <name-or-id>`

Update an existing route.

```bash
ops kong routes update payment-route --path /v2/payments --no-strip-path
```

#### `ops kong routes delete <name-or-id>`

Delete a route.

```bash
ops kong routes delete payment-route
```

> **Note:** The `--data-plane-only` option is available for route `create`, `update`, and `delete` operations.

---

### Consumer Commands

Manage API consumers and their credentials.

#### `ops kong consumers list`

List all consumers.

```bash
ops kong consumers list
ops kong consumers list --tag premium
```

#### `ops kong consumers get <username-or-id>`

Get consumer details.

```bash
ops kong consumers get mobile-app
```

#### `ops kong consumers create`

Create a new consumer.

```bash
ops kong consumers create \
  --username mobile-app \
  --custom-id app-12345 \
  --tag mobile \
  --tag production
```

**Options:**

| Option        | Description           |
| ------------- | --------------------- |
| `--username`  | Consumer username     |
| `--custom-id` | External ID reference |
| `--tag`       | Tag (repeatable)      |

Note: At least one of `--username` or `--custom-id` is required.

#### `ops kong consumers update <username-or-id>`

Update a consumer.

```bash
ops kong consumers update mobile-app --custom-id new-app-id
```

#### `ops kong consumers delete <username-or-id>`

Delete a consumer.

```bash
ops kong consumers delete mobile-app
```

> **Note:** The `--data-plane-only` option is available for consumer `create`, `update`, and `delete` operations.

#### `ops kong consumers credentials list <consumer>`

List all credentials for a consumer.

```bash
ops kong consumers credentials list mobile-app
```

**Output:**

```text
Credentials for: mobile-app
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Type        Key/ID                              Created
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
key-auth    abc123...xyz                        2024-01-15
key-auth    def456...uvw                        2024-02-20
jwt         mobile-app-jwt-key                  2024-01-15
oauth2      mobile-app-oauth                    2024-03-01
```

#### `ops kong consumers credentials add <consumer>`

Add a credential to a consumer.

```bash
# Add API key
ops kong consumers credentials add mobile-app \
  --type key-auth \
  --key "$YOUR_API_KEY"

# Add JWT credential
ops kong consumers credentials add mobile-app \
  --type jwt \
  --key "jwt-key-identifier" \
  --algorithm HS256 \
  --secret "$JWT_SECRET"

# Add OAuth2 application
ops kong consumers credentials add mobile-app \
  --type oauth2 \
  --name "Mobile App" \
  --client-id "mobile-app-client" \
  --client-secret "$CLIENT_SECRET" \
  --redirect-uri "https://app.example.com/callback"

# Add Basic Auth
ops kong consumers credentials add mobile-app \
  --type basic-auth \
  --username "app-user" \
  --password "$PASSWORD"

# Add HMAC credential
ops kong consumers credentials add mobile-app \
  --type hmac-auth \
  --username "hmac-user" \
  --secret "$HMAC_SECRET"
```

#### `ops kong consumers credentials delete <consumer> <credential-id>`

Remove a credential from a consumer.

```bash
ops kong consumers credentials delete mobile-app abc123-credential-id
```

---

### Upstream Commands

Manage load balancing and health checks.

#### `ops kong upstreams list`

List all upstreams.

```bash
ops kong upstreams list
```

#### `ops kong upstreams get <name-or-id>`

Get upstream details including health check configuration.

```bash
ops kong upstreams get payment-cluster
```

#### `ops kong upstreams create`

Create a new upstream for load balancing.

```bash
ops kong upstreams create \
  --name payment-cluster \
  --algorithm round-robin \
  --hash-on none \
  --slots 10000 \
  --tag production
```

**Options:**

| Option             | Description                                                      | Default     |
| ------------------ | ---------------------------------------------------------------- | ----------- |
| `--name`           | Upstream name (required)                                         | -           |
| `--algorithm`      | Load balancing algorithm                                         | round-robin |
| `--hash-on`        | Hash input (none, consumer, ip, header, cookie, path, query-arg) | none        |
| `--hash-on-header` | Header name for hash-on=header                                   | -           |
| `--hash-fallback`  | Fallback hash input                                              | none        |
| `--slots`          | Number of hash slots                                             | 10000       |
| `--tag`            | Tag (repeatable)                                                 | -           |

**Algorithms:**

- `round-robin`: Distribute requests evenly
- `consistent-hashing`: Hash-based distribution (sticky sessions)
- `least-connections`: Route to least loaded target
- `latency`: Route to lowest latency target

#### `ops kong upstreams update <name-or-id>`

Update an upstream.

```bash
ops kong upstreams update payment-cluster --algorithm least-connections
```

#### `ops kong upstreams delete <name-or-id>`

Delete an upstream.

```bash
ops kong upstreams delete payment-cluster
```

> **Note:** The `--data-plane-only` option is available for upstream `create`, `update`, and `delete` operations.

#### `ops kong upstreams targets list <upstream>`

List targets for an upstream.

```bash
ops kong upstreams targets list payment-cluster
```

**Output:**

```text
Targets for: payment-cluster
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Target                    Weight    Health    Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
192.168.1.10:8080         100       healthy   active
192.168.1.11:8080         100       healthy   active
192.168.1.12:8080         50        unhealthy DNS_ERROR
```

#### `ops kong upstreams targets add <upstream>`

Add a target to an upstream.

```bash
ops kong upstreams targets add payment-cluster \
  --target 192.168.1.13:8080 \
  --weight 100 \
  --tag new-node
```

**Options:**

| Option     | Description                           | Default |
| ---------- | ------------------------------------- | ------- |
| `--target` | Target address (host:port) (required) | -       |
| `--weight` | Traffic weight (0-65535)              | 100     |
| `--tag`    | Tag (repeatable)                      | -       |

#### `ops kong upstreams targets update <upstream> <target>`

Update an existing target's weight.

```bash
ops kong upstreams targets update payment-cluster 192.168.1.10:8080 --weight 200
```

**Options:**

| Option     | Description              |
| ---------- | ------------------------ |
| `--weight` | New traffic weight       |
| `--tag`    | Tags (replaces existing) |

#### `ops kong upstreams targets delete <upstream> <target>`

Remove a target from an upstream.

```bash
ops kong upstreams targets delete payment-cluster 192.168.1.12:8080
```

#### `ops kong upstreams targets healthy <upstream> <target>`

Manually mark a target as healthy.

```bash
ops kong upstreams targets healthy payment-cluster 192.168.1.12:8080
```

#### `ops kong upstreams targets unhealthy <upstream> <target>`

Manually mark a target as unhealthy.

```bash
ops kong upstreams targets unhealthy payment-cluster 192.168.1.12:8080
```

#### `ops kong upstreams health <upstream>`

Show health status for all targets in an upstream.

```bash
ops kong upstreams health payment-cluster
```

**Output:**

```text
Health Status: payment-cluster
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Target               Health     Active Checks    Passive Checks
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
192.168.1.10:8080    HEALTHY    5/5 success      0 failures
192.168.1.11:8080    HEALTHY    5/5 success      0 failures
192.168.1.12:8080    UNHEALTHY  0/5 success      3 timeouts
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Summary: 2/3 healthy (66%)
```

---

### Plugin Commands

Manage Kong plugins for extending gateway functionality.

#### `ops kong plugins list`

List enabled plugins.

```bash
ops kong plugins list
ops kong plugins list --service payment-api
ops kong plugins list --route payment-route
ops kong plugins list --consumer mobile-app
```

**Options:**

| Option            | Description           |
| ----------------- | --------------------- |
| `--service NAME`  | Filter by service     |
| `--route NAME`    | Filter by route       |
| `--consumer NAME` | Filter by consumer    |
| `--name PLUGIN`   | Filter by plugin name |

#### `ops kong plugins available`

List all available plugins on this Kong instance.

```bash
ops kong plugins available
ops kong plugins available --category security
```

**Output:**

```text
Available Kong Plugins
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Category        Plugin                  Bundled    Enterprise
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Authentication  key-auth                Yes        No
                jwt                     Yes        No
                oauth2                  Yes        No
                basic-auth              Yes        No
                hmac-auth               Yes        No
                ldap-auth               Yes        No
                openid-connect          No         Yes
Security        acl                     Yes        No
                ip-restriction          Yes        No
                bot-detection           Yes        No
                cors                    Yes        No
Traffic         rate-limiting           Yes        No
                rate-limiting-advanced  No         Yes
                request-size-limiting   Yes        No
                request-termination     Yes        No
Transformation  request-transformer     Yes        No
                response-transformer    Yes        No
                correlation-id          Yes        No
Logging         file-log                Yes        No
                http-log                Yes        No
                tcp-log                 Yes        No
                syslog                  Yes        No
                prometheus              Yes        No
                opentelemetry           Yes        No
```

#### `ops kong plugins get <id>`

Get plugin configuration details.

```bash
ops kong plugins get abc123-plugin-id
```

#### `ops kong plugins enable`

Enable a plugin on a service, route, consumer, or globally.

```bash
# Enable rate limiting on a service
ops kong plugins enable rate-limiting \
  --service payment-api \
  --config minute=100 \
  --config hour=5000 \
  --config policy=local

# Enable JWT authentication on a route
ops kong plugins enable jwt \
  --route payment-route \
  --config claims_to_verify=exp,nbf

# Enable key-auth globally
ops kong plugins enable key-auth

# Enable CORS on a service
ops kong plugins enable cors \
  --service payment-api \
  --config origins=https://example.com,https://app.example.com \
  --config methods=GET,POST,PUT,DELETE \
  --config headers=Accept,Authorization,Content-Type \
  --config credentials=true \
  --config max_age=3600
```

**Options:**

| Option                 | Description                       |
| ---------------------- | --------------------------------- |
| `--service NAME`       | Apply to service                  |
| `--route NAME`         | Apply to route                    |
| `--consumer NAME`      | Apply to consumer                 |
| `--config KEY=VALUE`   | Plugin configuration (repeatable) |
| `--enabled/--disabled` | Enable or disable plugin          |
| `--tag`                | Tag (repeatable)                  |

#### `ops kong plugins update <id>`

Update plugin configuration.

```bash
ops kong plugins update abc123-plugin-id --config minute=200 --config hour=10000
```

#### `ops kong plugins disable <id>`

Disable a plugin (without deleting).

```bash
ops kong plugins disable abc123-plugin-id
```

> **Note:** The `--data-plane-only` option is available for plugin `enable`, `update`, and `disable` operations.

---

### Security

Configure authentication, authorization, and security plugins.

#### `ops kong security key-auth`

Configure key-based authentication.

```bash
# Enable key-auth on a service
ops kong security key-auth enable \
  --service payment-api \
  --key-names apikey,x-api-key \
  --hide-credentials

# Create API key for a consumer
ops kong security key-auth create-key mobile-app \
  --key "$YOUR_API_KEY" \
  --tag production

# List keys for a consumer
ops kong security key-auth list-keys mobile-app

# Revoke an API key
ops kong security key-auth revoke-key mobile-app abc123-key-id
```

**Options for `enable`:**

| Option                               | Description                      | Default |
| ------------------------------------ | -------------------------------- | ------- |
| `--key-names`                        | Header/query param names         | apikey  |
| `--hide-credentials`                 | Remove key from upstream request | false   |
| `--key-in-header/--no-key-in-header` | Accept key in header             | true    |
| `--key-in-query/--no-key-in-query`   | Accept key in query string       | true    |
| `--key-in-body/--no-key-in-body`     | Accept key in body               | false   |

#### `ops kong security jwt`

Configure JWT authentication.

```bash
# Enable JWT on a service
ops kong security jwt enable \
  --service payment-api \
  --claims-to-verify exp,nbf \
  --key-claim-name iss \
  --header-names Authorization

# Add JWT credential to consumer
ops kong security jwt add-credential mobile-app \
  --key "jwt-key-id" \
  --algorithm RS256 \
  --rsa-public-key @/path/to/public.pem

# List JWT credentials
ops kong security jwt list-credentials mobile-app
```

**Supported Algorithms:** HS256, HS384, HS512, RS256, RS384, RS512, ES256, ES384, ES512

#### `ops kong security oauth2`

Configure OAuth 2.0 authentication.

```bash
# Enable OAuth2 on a service
ops kong security oauth2 enable \
  --service payment-api \
  --scopes read,write,admin \
  --mandatory-scope \
  --provision-key "$PROVISION_KEY" \
  --token-expiration 7200 \
  --enable-authorization-code \
  --enable-client-credentials

# Create OAuth2 application for consumer
ops kong security oauth2 create-app mobile-app \
  --name "Mobile Application" \
  --client-id "mobile-client-id" \
  --client-secret "$CLIENT_SECRET" \
  --redirect-uri "https://app.example.com/oauth/callback"
```

#### `ops kong security acl`

Configure Access Control Lists.

```bash
# Enable ACL on a service (allow specific groups)
ops kong security acl enable \
  --service payment-api \
  --allow admin,premium-users

# Enable ACL with deny list
ops kong security acl enable \
  --service internal-api \
  --deny blocked-users

# Add consumer to ACL group
ops kong security acl add-group mobile-app premium-users

# Remove consumer from group
ops kong security acl remove-group mobile-app premium-users

# List consumer's groups
ops kong security acl list-groups mobile-app
```

#### `ops kong security ip-restriction`

Configure IP-based access control.

```bash
# Allow specific IPs
ops kong security ip-restriction enable \
  --service admin-api \
  --allow 10.0.0.0/8 \
  --allow 192.168.1.100

# Deny specific IPs
ops kong security ip-restriction enable \
  --route public-route \
  --deny 203.0.113.0/24

# Status codes and messages
ops kong security ip-restriction enable \
  --service payment-api \
  --deny 198.51.100.0/24 \
  --status 403 \
  --message "Access denied from your location"
```

#### `ops kong security cors`

Configure Cross-Origin Resource Sharing.

```bash
ops kong security cors enable \
  --service payment-api \
  --origins "https://example.com" \
  --origins "https://app.example.com" \
  --methods GET,POST,PUT,DELETE,OPTIONS \
  --headers Accept,Authorization,Content-Type,X-Request-ID \
  --exposed-headers X-Auth-Token,X-Request-ID \
  --credentials \
  --max-age 3600 \
  --preflight-continue
```

#### `ops kong security mtls`

Configure mutual TLS authentication.

```bash
# Enable mTLS on a service
ops kong security mtls enable \
  --service payment-api \
  --ca-certificate @/path/to/ca.crt \
  --skip-consumer-lookup \
  --revocation-check-mode IGNORE_CA_ERROR

# Add certificate to consumer
ops kong security mtls add-cert mobile-app \
  --certificate @/path/to/client.crt

# List consumer certificates
ops kong security mtls list-certs mobile-app
```

---

### Traffic Control

Configure rate limiting, request transformation, and traffic policies.

#### `ops kong traffic rate-limit`

Configure rate limiting.

```bash
# Show current rate limit config
ops kong traffic rate-limit get --service payment-api

# Set rate limits
ops kong traffic rate-limit enable \
  --service payment-api \
  --second 10 \
  --minute 100 \
  --hour 5000 \
  --day 50000 \
  --policy local \
  --limit-by consumer \
  --fault-tolerant \
  --hide-client-headers \
  --error-code 429 \
  --error-message "Rate limit exceeded. Please slow down."

# Set rate limit on a route
ops kong traffic rate-limit enable \
  --route high-traffic-route \
  --minute 1000 \
  --policy redis \
  --redis-host redis.example.com \
  --redis-port 6379

# Remove rate limiting
ops kong traffic rate-limit disable --service payment-api
```

**Rate Limit Options:**

| Option                  | Description                                                 |
| ----------------------- | ----------------------------------------------------------- |
| `--second N`            | Requests per second                                         |
| `--minute N`            | Requests per minute                                         |
| `--hour N`              | Requests per hour                                           |
| `--day N`               | Requests per day                                            |
| `--month N`             | Requests per month                                          |
| `--year N`              | Requests per year                                           |
| `--policy`              | Counter storage (local, cluster, redis)                     |
| `--limit-by`            | Limit key (consumer, credential, ip, service, header, path) |
| `--header-name`         | Header name for limit-by=header                             |
| `--path`                | Path for limit-by=path                                      |
| `--fault-tolerant`      | Continue if counter fails                                   |
| `--hide-client-headers` | Don't expose rate limit headers                             |

#### `ops kong traffic request-size`

Limit request body size.

```bash
ops kong traffic request-size set \
  --service upload-api \
  --allowed-payload-size 10 \
  --size-unit megabytes \
  --require-content-length
```

#### `ops kong traffic request-transformer`

Transform incoming requests.

```bash
ops kong traffic request-transformer enable \
  --service payment-api \
  --add-header "X-Service:payment" \
  --add-header "X-Version:v1" \
  --add-querystring "source=api" \
  --rename-header "X-Old-Header:X-New-Header" \
  --remove-header "X-Internal-Only" \
  --replace-body-param "oldField:newField"
```

#### `ops kong traffic response-transformer`

Transform outgoing responses.

```bash
ops kong traffic response-transformer enable \
  --service payment-api \
  --add-header "X-Powered-By:Kong" \
  --remove-header "Server" \
  --remove-header "X-Kong-Upstream-Latency" \
  --add-json "version:1.0" \
  --add-json "api:payment"
```

---

### Observability

Configure logging, metrics, and health monitoring.

#### `ops kong observability logs`

Configure logging plugins.

```bash
# HTTP logging
ops kong observability logs http enable \
  --service payment-api \
  --http-endpoint "https://logs.example.com/ingest" \
  --method POST \
  --content-type "application/json" \
  --timeout 10000 \
  --keepalive 60000 \
  --retry-count 3

# File logging
ops kong observability logs file enable \
  --service payment-api \
  --path "/var/log/kong/payment-api.log" \
  --reopen

# Syslog
ops kong observability logs syslog enable \
  --service payment-api \
  --host syslog.example.com \
  --port 514 \
  --facility local0 \
  --severity info

# TCP logging
ops kong observability logs tcp enable \
  --service payment-api \
  --host logs.example.com \
  --port 5000 \
  --tls \
  --tls-sni logs.example.com
```

#### `ops kong observability metrics`

Configure Prometheus metrics.

```bash
# Enable Prometheus metrics globally
ops kong observability metrics prometheus enable \
  --per-consumer \
  --status-code-metrics \
  --latency-metrics \
  --bandwidth-metrics \
  --upstream-health-metrics

# Show metrics endpoint info
ops kong observability metrics prometheus info
```

**Output:**

```text
Prometheus Metrics Configuration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Endpoint:          http://localhost:8001/metrics
Per Consumer:      Yes
Status Codes:      Yes
Latency:           Yes
Bandwidth:         Yes
Upstream Health:   Yes
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Scrape Config (for prometheus.yml):
  - job_name: 'kong'
    static_configs:
      - targets: ['kong:8001']
```

#### `ops kong observability health`

Configure health checks for upstreams.

```bash
# Show health check config
ops kong observability health show payment-cluster

# Configure active health checks
ops kong observability health set payment-cluster \
  --active-type http \
  --active-http-path /health \
  --active-timeout 5 \
  --active-concurrency 10 \
  --active-interval-healthy 10 \
  --active-interval-unhealthy 5 \
  --active-successes-healthy 2 \
  --active-failures-unhealthy 3 \
  --active-http-statuses-healthy 200,201,204 \
  --active-http-statuses-unhealthy 500,502,503

# Configure passive health checks
ops kong observability health set payment-cluster \
  --passive-type http \
  --passive-successes-healthy 5 \
  --passive-failures-unhealthy 3 \
  --passive-http-statuses-healthy 200,201,204 \
  --passive-http-statuses-unhealthy 500,502,503,504 \
  --passive-timeouts-unhealthy 3
```

#### `ops kong observability tracing`

Configure distributed tracing.

```bash
# OpenTelemetry
ops kong observability tracing opentelemetry enable \
  --endpoint "http://otel-collector:4318/v1/traces" \
  --header "Authorization:Bearer token" \
  --resource-attribute "service.name=kong-gateway" \
  --resource-attribute "deployment.environment=production"

# Zipkin
ops kong observability tracing zipkin enable \
  --http-endpoint "http://zipkin:9411/api/v2/spans" \
  --sample-ratio 0.1 \
  --include-credential
```

#### External Metrics Queries

Query metrics from an external Prometheus instance.

```bash
# Execute custom PromQL query
ops kong observability metrics query exec 'rate(kong_http_requests_total[5m])'
ops kong observability metrics query exec 'kong_upstream_target_health' --range 1h

# Show request rate (requests/second)
ops kong observability metrics query rate
ops kong observability metrics query rate --service my-api

# Show latency percentiles (p50, p90, p99)
ops kong observability metrics query latency
ops kong observability metrics query latency --service my-api

# Show error rate (4xx + 5xx responses)
ops kong observability metrics query errors
ops kong observability metrics query errors --service my-api

# Show metrics summary
ops kong observability metrics query summary
ops kong observability metrics query summary --service my-api
```

**Options:**

| Option            | Description                         | Default |
| ----------------- | ----------------------------------- | ------- |
| `--range`, `-r`   | Time range (e.g., '5m', '1h', '1d') | 1h      |
| `--step`          | Query resolution step               | 1m      |
| `--service`, `-s` | Filter by service name              | -       |
| `--route`, `-r`   | Filter by route name                | -       |
| `--output`        | Output format (table, json, yaml)   | table   |

#### External Log Search

Search logs from Elasticsearch or Loki.

```bash
# Search logs with text query
ops kong observability logs search query "error"
ops kong observability logs search query --service my-api
ops kong observability logs search query --status 500 --range 1d

# Show error logs (4xx and 5xx)
ops kong observability logs search errors
ops kong observability logs search errors --service my-api --range 1d

# Show log statistics summary
ops kong observability logs search summary
ops kong observability logs search summary --service my-api
```

**Options:**

| Option            | Description                       | Default |
| ----------------- | --------------------------------- | ------- |
| `--service`, `-s` | Filter by service name            | -       |
| `--route`, `-r`   | Filter by route name              | -       |
| `--status`        | Filter by status code             | -       |
| `--range`         | Time range (e.g., '1h', '1d')     | 1h      |
| `--limit`, `-l`   | Maximum results                   | 50      |
| `--output`        | Output format (table, json, yaml) | table   |

#### External Trace Search

Query traces from Jaeger or Zipkin.

```bash
# Find traces
ops kong observability tracing traces find
ops kong observability tracing traces find --route my-route
ops kong observability tracing traces find --min-duration 500

# Get a specific trace
ops kong observability tracing traces get abc123def456

# Find slow traces (above threshold)
ops kong observability tracing traces slow
ops kong observability tracing traces slow --threshold 1000

# Find traces with errors
ops kong observability tracing traces errors
ops kong observability tracing traces errors --range 1d

# Analyze a trace for performance insights
ops kong observability tracing traces analyze abc123def456

# Show tracing statistics summary
ops kong observability tracing traces summary
ops kong observability tracing traces summary --range 1d
```

**Options:**

| Option              | Description                        | Default |
| ------------------- | ---------------------------------- | ------- |
| `--route`, `-r`     | Filter by route name               | -       |
| `--status`          | Filter by status code              | -       |
| `--min-duration`    | Minimum duration in milliseconds   | -       |
| `--threshold`, `-t` | Duration threshold for slow traces | 500     |
| `--range`           | Time range (e.g., '1h', '1d')      | 1h      |
| `--limit`, `-l`     | Maximum results                    | 20      |
| `--output`          | Output format (table, json, yaml)  | table   |

---

### Declarative Configuration (DB-less Mode)

Manage Kong configuration as code for DB-less deployments.

#### `ops kong config export`

Export current Kong configuration to YAML.

```bash
# Export full configuration
ops kong config export kong-config.yaml

# Export specific resources
ops kong config export kong-services.yaml --only services,routes

# Export with credentials (caution!)
ops kong config export kong-full.yaml --include-credentials

# Export to stdout
ops kong config export -
```

**Output File Example:**

```yaml
_format_version: "3.0"

services:
  - name: payment-api
    host: payment.internal.example.com
    port: 8080
    protocol: http
    path: /api/v1
    tags:
      - production
      - payments
    routes:
      - name: payment-route
        paths:
          - /payments
          - /transactions
        methods:
          - GET
          - POST
        strip_path: true
    plugins:
      - name: rate-limiting
        config:
          minute: 100
          hour: 5000
          policy: local

upstreams:
  - name: payment-cluster
    algorithm: round-robin
    healthchecks:
      active:
        type: http
        http_path: /health
        healthy:
          interval: 10
          successes: 2
        unhealthy:
          interval: 5
          http_failures: 3
    targets:
      - target: 192.168.1.10:8080
        weight: 100
      - target: 192.168.1.11:8080
        weight: 100

consumers:
  - username: mobile-app
    custom_id: app-12345
    tags:
      - mobile
      - production
```

#### `ops kong config validate <file>`

Validate a declarative configuration file.

```bash
ops kong config validate kong-config.yaml
```

**Output (Success):**

```text
Validation Results: kong-config.yaml
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

**Output (Errors):**

```text
Validation Results: kong-config.yaml
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Errors:
  1. services[0].host: required field missing
  2. routes[2].service: references unknown service 'unknown-api'
  3. plugins[1].config.minute: must be a positive integer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Status:          INVALID (3 errors)
```

#### `ops kong config diff <file>`

Compare configuration file with current Kong state.

```bash
ops kong config diff kong-config.yaml
```

**Output:**

```text
Configuration Diff: kong-config.yaml vs Current State
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Services:
  + payment-api-v2 (new)
  ~ payment-api (modified)
      - port: 8080 -> 8443
      - protocol: http -> https
  - legacy-api (removed)

Routes:
  + payment-v2-route (new)
  ~ payment-route (modified)
      - paths: [/payments] -> [/payments, /pay]

Plugins:
  + jwt on service:payment-api-v2 (new)
  ~ rate-limiting on service:payment-api (modified)
      - config.minute: 100 -> 200
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Summary: 3 additions, 3 modifications, 1 removal
```

#### `ops kong config apply <file>`

Apply declarative configuration to Kong (DB-less mode).

```bash
# Apply configuration
ops kong config apply kong-config.yaml

# Apply with confirmation prompt
ops kong config apply kong-config.yaml --confirm

# Dry run (show what would change)
ops kong config apply kong-config.yaml --dry-run
```

**Output:**

```text
Applying Configuration: kong-config.yaml
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Validating configuration... OK
Uploading to Kong... OK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Configuration applied successfully!

Entities loaded:
  Services:    3
  Routes:      8
  Consumers:   15
  Upstreams:   2
  Plugins:     12
```

#### `ops kong config generate`

Interactively generate a declarative configuration file.

```bash
ops kong config generate kong-config.yaml
```

Launches an interactive wizard to build configuration.

---

### Service Registry

Manage services locally and deploy them to Kong in batch. The registry provides
a local configuration file for defining services with optional OpenAPI integration.

#### Configuration

The registry stores service definitions in `~/.config/ops/kong/services.yaml`:

```yaml
services:
  - name: auth-service
    host: auth-service.auth-service.svc.cluster.local
    port: 8080
    protocol: http
    tags: [microservice, auth]
    openapi_spec: ~/repos/auth-service/openapi.yaml # Optional
    path_prefix: /api/v1/auth # For route sync

  - name: recipe-management-service
    host: recipe-management.recipe-management.svc.cluster.local
    port: 8080
    openapi_spec: ~/repos/recipe-service/openapi.yaml
    path_prefix: /api/v1/recipes

  - name: admin-ui-service
    host: admin-ui.admin-ui.svc.cluster.local
    port: 4000
    # No openapi_spec - static UI, routes added separately
```

#### `ops kong registry list`

List all services in the registry.

```bash
ops kong registry list
ops kong registry list --output json
ops kong registry list --output yaml
```

**Output:**

```text
Service Registry
┏━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Name                     ┃ Host                                         ┃ Port  ┃ Protocol ┃ OpenAPI Spec ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ auth-service             │ auth-service.auth-service.svc.cluster.local  │ 8080  │ http     │ openapi.yaml │
│ recipe-management-service│ recipe-management.svc.cluster.local          │ 8080  │ http     │ openapi.yaml │
│ admin-ui-service         │ admin-ui.admin-ui.svc.cluster.local          │ 4000  │ http     │ -            │
└──────────────────────────┴──────────────────────────────────────────────┴───────┴──────────┴──────────────┘

Total: 3 services
Registry: ~/.config/ops/kong/services.yaml
```

#### `ops kong registry show <name>`

Show details for a single service.

```bash
ops kong registry show auth-service
```

#### `ops kong registry add <name>`

Add a new service to the registry.

```bash
# Basic service
ops kong registry add auth-service --host auth.local --port 8080

# With tags
ops kong registry add api-service --host api.local --tag prod --tag api

# With OpenAPI spec for route sync
ops kong registry add users-service --host users.local \
  --openapi-spec ./specs/users.yaml \
  --path-prefix /api/v1/users
```

**Options:**

| Option           | Description                                      |
| ---------------- | ------------------------------------------------ |
| `--host`         | Upstream host (required)                         |
| `--port`         | Upstream port (default: 80)                      |
| `--protocol`     | Protocol: http, https, grpc (default: http)      |
| `--tag`          | Tags (can be repeated)                           |
| `--openapi-spec` | Path to OpenAPI spec for route sync              |
| `--path-prefix`  | Route path prefix for OpenAPI sync               |
| `--strip-path`   | Strip matched path when proxying (default: true) |

#### `ops kong registry remove <name>`

Remove a service from the registry.

```bash
ops kong registry remove auth-service
ops kong registry remove auth-service --force  # Skip confirmation
```

#### `ops kong registry import <file>`

Import services from a YAML file into the registry.

```bash
ops kong registry import services.yaml
```

Services with existing names are updated; new services are added.

#### `ops kong registry deploy`

Deploy all services from registry to Kong and optionally sync routes from OpenAPI specs.

```bash
# Preview changes
ops kong registry deploy --dry-run

# Deploy all services
ops kong registry deploy

# Deploy without route sync
ops kong registry deploy --skip-routes

# Deploy specific service only
ops kong registry deploy --service auth-service

# Skip confirmation
ops kong registry deploy --no-confirm
```

**Options:**

| Option          | Description                        |
| --------------- | ---------------------------------- |
| `--dry-run`     | Preview changes without applying   |
| `--skip-routes` | Skip OpenAPI route synchronization |
| `--service`     | Deploy only this service           |
| `--no-confirm`  | Skip confirmation prompt           |

**Output:**

```text
Service Deployment Preview
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Total: 3  Create: 2  Update: 1  Unchanged: 0                 ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Services to Create
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━┓
┃ Service Name   ┃ Host                  ┃ Port ┃ Protocol ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━┩
│ auth-service   │ auth.local            │ 8080 │ http     │
│ users-service  │ users.local           │ 8080 │ http     │
└────────────────┴───────────────────────┴──────┴──────────┘

Services to Update
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Service Name   ┃ Changes                                   ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ api-service    │ host: old.local -> new.local              │
└────────────────┴───────────────────────────────────────────┘

2 service(s) have OpenAPI specs - routes will be synced after service creation

Apply these changes? [y/N]:
```

#### Workflow Example

```bash
# 1. Add services to registry
ops kong registry add auth-service --host auth.local --port 8080 \
  --openapi-spec ./auth-api.yaml --path-prefix /api/v1/auth

ops kong registry add users-service --host users.local --port 8080 \
  --openapi-spec ./users-api.yaml --path-prefix /api/v1/users

# 2. Preview deployment
ops kong registry deploy --dry-run

# 3. Deploy services to Kong
ops kong registry deploy

# 4. Verify services in Kong
ops kong services list
```

---

### Deployment Management

Commands for installing, upgrading, and managing Kong Gateway deployments in Kubernetes.

#### `ops kong deploy status`

Show Kong Gateway deployment status.

```bash
ops kong deploy status
ops kong deploy status --output json
```

**Output:**

```text
Kong Deployment Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Property        Value
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Status          Running
Namespace       kong
Chart           kong/ingress
Chart Version   0.13.1
App Version     3.4.0
PostgreSQL      Ready
Gateway         Ready
Controller      Ready
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Pods
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Name                          Phase     Ready    Restarts
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
kong-gateway-abc123           Running   Yes      0
kong-controller-xyz789        Running   Yes      0
kong-postgres-0               Running   Yes      0
```

#### `ops kong deploy install`

Install Kong Gateway with PostgreSQL.

```bash
ops kong deploy install
ops kong deploy install --force
```

This command:

1. Sets up the Kong Helm repository
2. Creates the kong namespace
3. Creates the PostgreSQL secret from `config/.env.kong.secrets`
4. Deploys PostgreSQL
5. Installs Kong Gateway using the `kong/ingress` chart

**Prerequisites:**

- Kubernetes cluster access (kubectl configured)
- Helm 3 installed
- `config/.env.kong.secrets` file exists

**Options:**

| Option    | Description                    |
| --------- | ------------------------------ |
| `--force` | Reinstall without confirmation |

#### `ops kong deploy upgrade`

Upgrade Kong Gateway to latest configuration.

```bash
ops kong deploy upgrade
```

Updates the Kong deployment with changes from `kong-values.yaml`. PostgreSQL is not affected.

#### `ops kong deploy uninstall`

Uninstall Kong Gateway.

```bash
ops kong deploy uninstall
ops kong deploy uninstall --delete-secrets --delete-pvc
ops kong deploy uninstall --force
```

By default, keeps secrets and PVC for easier reinstallation.

**Options:**

| Option                            | Description                             | Default |
| --------------------------------- | --------------------------------------- | ------- |
| `--keep-postgres`                 | Keep PostgreSQL database                | false   |
| `--keep-secrets/--delete-secrets` | Keep or delete secrets                  | keep    |
| `--keep-pvc/--delete-pvc`         | Keep or delete persistent volume claims | keep    |
| `--force`                         | Skip confirmation prompt                | false   |

#### `ops kong deploy init`

Initialize deployment configuration files.

```bash
ops kong deploy init
ops kong deploy init --force
```

Creates the secrets file from the example template if it doesn't exist.

---

### OpenAPI Integration

Manage Kong routes from OpenAPI specifications.

#### `ops kong openapi sync-routes`

Sync Kong routes from an OpenAPI specification.

```bash
# Sync routes from spec
ops kong openapi sync-routes api-spec.yaml --service auth-service

# Preview changes (dry run)
ops kong openapi sync-routes api-spec.yaml --service auth-service --dry-run

# Force sync with breaking changes
ops kong openapi sync-routes api-spec.yaml --service auth-service --force

# Sync with path prefix
ops kong openapi sync-routes api.json --service my-api --path-prefix /v2
```

Creates, updates, or deletes routes to match the OpenAPI spec. Routes are named using
the pattern: `{service}-{operationId}`.

**Breaking changes (require --force):**

- Removed paths (routes that exist in Kong but not in spec)
- Removed HTTP methods from existing routes
- Path structure changes

**Options:**

| Option                         | Description                       | Default |
| ------------------------------ | --------------------------------- | ------- |
| `--service`, `-s`              | Kong service name (required)      | -       |
| `--path-prefix`                | Prefix to add to all route paths  | -       |
| `--strip-path/--no-strip-path` | Strip matched path when proxying  | strip   |
| `--dry-run`                    | Preview changes without applying  | false   |
| `--force`                      | Apply breaking changes            | false   |
| `--output`                     | Output format (table, json, yaml) | table   |

**Output:**

```text
Parsed: Payment API v1.0 (8 operations)
Generated 8 route mappings

┌─ Sync Preview: payment-api ─────────────────────────────────────┐
│ Creates: 3  Updates: 2  Deletes: 1  (1 breaking)                │
└─────────────────────────────────────────────────────────────────┘

Creates
┏━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Route Name            ┃ Path              ┃ Methods     ┃
┡━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ payment-api-create    │ /payments         │ POST        │
│ payment-api-get       │ /payments/{id}    │ GET         │
│ payment-api-list      │ /payments         │ GET         │
└───────────────────────┴───────────────────┴─────────────┘
```

#### `ops kong openapi diff`

Show diff between OpenAPI spec and current Kong routes.

```bash
# Preview differences
ops kong openapi diff api-spec.yaml --service auth-service

# Verbose output with field changes
ops kong openapi diff api-spec.yaml --service auth-service --verbose

# JSON output
ops kong openapi diff api-spec.yaml --service auth-service --output json
```

**Options:**

| Option                         | Description                       |
| ------------------------------ | --------------------------------- |
| `--service`, `-s`              | Kong service name (required)      |
| `--path-prefix`                | Prefix to add to all route paths  |
| `--strip-path/--no-strip-path` | Strip matched path when proxying  |
| `--verbose`, `-v`              | Show detailed field changes       |
| `--output`                     | Output format (table, json, yaml) |

---

### Konnect Commands

Commands for configuring and managing Kong Konnect integration.

#### `ops kong konnect login`

Configure Konnect credentials.

```bash
# Interactive login
ops kong konnect login

# Login with token and region
ops kong konnect login --token $KONNECT_TOKEN --region us

# Force overwrite existing config
ops kong konnect login --force
```

**Options:**

| Option           | Description                              |
| ---------------- | ---------------------------------------- |
| `--token`, `-t`  | Konnect Personal Access Token            |
| `--region`, `-r` | Konnect region (us, eu, au). Default: us |
| `--force`, `-f`  | Overwrite existing configuration         |

#### `ops kong konnect setup`

Set up Konnect data plane connection. Creates TLS certificates and Kubernetes secrets
needed for Kong Gateway to connect to Konnect control plane.

```bash
# Interactive setup (prompts for control plane)
ops kong konnect setup

# Specify control plane
ops kong konnect setup --control-plane my-control-plane

# Update Helm values file with Konnect endpoints
ops kong konnect setup --control-plane my-cp --update-values

# Custom values file path
ops kong konnect setup --control-plane my-cp --update-values --values-file ./custom-values.yaml

# Custom secret name and namespace
ops kong konnect setup --control-plane my-cp --namespace kong-system --secret-name my-tls
```

**Options:**

| Option              | Description                                                 |
| ------------------- | ----------------------------------------------------------- |
| `--control-plane`   | Control plane name or ID                                    |
| `--namespace`, `-n` | Kubernetes namespace for the secret (default: kong)         |
| `--secret-name`     | Name for the TLS secret (default: konnect-client-tls)       |
| `--update-values`   | Update Helm values file with Konnect endpoints              |
| `--values-file`     | Path to values file (default: k8s/gateway/kong-values.yaml) |
| `--force`, `-f`     | Overwrite existing certificate/secret                       |

#### `ops kong konnect status`

Show Konnect configuration status.

```bash
ops kong konnect status
```

**Output:**

```text
Konnect Configuration

Region: us
API URL: https://us.api.konghq.com
Default Control Plane: my-control-plane
Config File: ~/.config/ops/konnect.yaml

✓ Authenticated
```

#### `ops kong konnect list-control-planes`

List available control planes.

```bash
ops kong konnect list-control-planes
```

**Output:**

```text
Control Planes (3)
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name               ┃ ID                                   ┃ Type        ┃ Endpoint                     ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ production         │ abc123-def456-789                    │ CLUSTER     │ us.cp.konghq.com:443         │
│ staging            │ xyz789-abc123-456                    │ CLUSTER     │ us.cp.konghq.com:443         │
│ development        │ def456-xyz789-123                    │ CLUSTER     │ us.cp.konghq.com:443         │
└────────────────────┴──────────────────────────────────────┴─────────────┴──────────────────────────────┘
```

---

### Sync Commands

Monitor and synchronize state between Kong Gateway and Konnect control plane.

> **Interactive Conflict Resolution**: When entities have configuration drift between
> Gateway and Konnect, use `--interactive` to launch a TUI for resolving conflicts.
> See [Interactive Conflict Resolution](./conflict-resolution.md)
> for detailed documentation.

#### Supported Entity Types

The sync commands support the following Kong entity types:

| Entity Type       | Description                     | Sync Support |
| ----------------- | ------------------------------- | ------------ |
| `services`        | Backend API/service definitions | Full         |
| `routes`          | Request routing rules           | Full         |
| `consumers`       | API consumers                   | Full         |
| `plugins`         | Kong plugins                    | Full         |
| `upstreams`       | Load balancer upstreams         | Full         |
| `certificates`    | TLS certificates for SSL/mTLS   | Full         |
| `snis`            | Server Name Indications         | Full         |
| `ca_certificates` | CA certificates for mTLS        | Full         |
| `key_sets`        | Cryptographic key collections   | Full         |
| `keys`            | Cryptographic keys (JWT, etc.)  | Full         |
| `vaults`          | Secret backends (Enterprise)    | Full         |

#### `ops kong sync status`

Show drift between Gateway and Konnect configurations.

```bash
# Check all entity types
ops kong sync status

# Check specific entity type
ops kong sync status --type services

# Output as JSON
ops kong sync status --output json
```

**Output:**

```text
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

**Options:**

| Option            | Description                                             |
| ----------------- | ------------------------------------------------------- |
| `--type`, `-t`    | Entity type to check (see Supported Entity Types above) |
| `--output FORMAT` | Output format (table, json, yaml)                       |

**Examples:**

```bash
# Check sync status for certificates
ops kong sync status --type certificates

# Check sync status for key sets
ops kong sync status --type key_sets

# Check sync status for all TLS-related entities
ops kong sync status --type certificates
ops kong sync status --type snis
ops kong sync status --type ca_certificates
```

#### `ops kong sync push`

Push Gateway configuration to Konnect.

```bash
# Push all entity types
ops kong sync push

# Push specific entity type
ops kong sync push --type services

# Preview changes without applying
ops kong sync push --dry-run

# Push without confirmation
ops kong sync push --force
```

**Output (dry run):**

```text
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

**Output (push):**

```text
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

**Options:**

| Option                | Description                                                           |
| --------------------- | --------------------------------------------------------------------- |
| `--type`, `-t`        | Entity type to push (see Supported Entity Types above)                |
| `--dry-run`, `-n`     | Show what would be pushed without making changes                      |
| `--include-targets`   | Also sync targets when syncing upstreams                              |
| `--force`, `-f`       | Push without confirmation prompt                                      |
| `--interactive`, `-i` | Launch TUI for interactive conflict resolution when drift is detected |
| `--skip-conflicts`    | Skip entities with conflicts (sync only non-conflicting entities)     |

> **Note:** `--interactive` and `--skip-conflicts` are mutually exclusive options.

**Examples:**

```bash
# Preview sync for services only
ops kong sync push --type services --dry-run

# Push all changes without confirmation
ops kong sync push --force

# Interactive conflict resolution (launches TUI when drift detected)
ops kong sync push --interactive

# Skip conflicting entities, sync only clean ones
ops kong sync push --skip-conflicts --force

# Push only routes to Konnect
ops kong sync push --type routes --force

# Push upstreams with their targets
ops kong sync push --type upstreams --include-targets --force

# Push TLS certificates to Konnect
ops kong sync push --type certificates --dry-run
ops kong sync push --type certificates --force

# Push SNIs (Server Name Indications) to Konnect
ops kong sync push --type snis --force

# Push CA certificates for mTLS
ops kong sync push --type ca_certificates --force

# Push cryptographic keys and key sets
ops kong sync push --type key_sets --force
ops kong sync push --type keys --force

# Push vault configurations (Enterprise)
ops kong sync push --type vaults --force
```

#### `ops kong sync pull`

Pull Konnect configuration to Gateway.

```bash
# Pull all entity types
ops kong sync pull

# Pull specific entity type
ops kong sync pull --type services

# Preview changes without applying
ops kong sync pull --dry-run

# Pull and update drifted entities
ops kong sync pull --with-drift --force

# Pull without confirmation
ops kong sync pull --force
```

**Output (dry run):**

```text
Sync Preview (dry run)

Services:
  Would create: konnect-only-service

Summary:
  Would create: 1 entity(s)
```

**Output (pull with drift):**

```text
Pulling Konnect -> Gateway

Services:
  Created: konnect-only-service
  Updated: drifted-service

Summary:
  Created: 1 entity(s)
  Updated: 1 entity(s)
✓ Sync complete
```

**Options:**

| Option                | Description                                                           |
| --------------------- | --------------------------------------------------------------------- |
| `--type`, `-t`        | Entity type to pull (see Supported Entity Types above)                |
| `--dry-run`, `-n`     | Show what would be pulled without making changes                      |
| `--with-drift`        | Also update entities with drift (Gateway to match Konnect)            |
| `--include-targets`   | Also sync targets when syncing upstreams                              |
| `--force`, `-f`       | Pull without confirmation prompt                                      |
| `--interactive`, `-i` | Launch TUI for interactive conflict resolution when drift is detected |
| `--skip-conflicts`    | Skip entities with conflicts (sync only non-conflicting entities)     |

> **Note:** `--interactive` and `--skip-conflicts` are mutually exclusive options.

**Examples:**

```bash
# Preview what would be pulled
ops kong sync pull --dry-run

# Pull only services from Konnect
ops kong sync pull --type services --force

# Pull and sync drifted entities
ops kong sync pull --with-drift --force

# Interactive conflict resolution for pull (launches TUI)
ops kong sync pull --with-drift --interactive

# Skip conflicts, pull only non-conflicting entities
ops kong sync pull --with-drift --skip-conflicts --force

# Pull upstreams with their targets
ops kong sync pull --type upstreams --include-targets --force

# Pull TLS certificates from Konnect
ops kong sync pull --type certificates --dry-run
ops kong sync pull --type certificates --force

# Pull SNIs from Konnect
ops kong sync pull --type snis --force

# Pull CA certificates from Konnect
ops kong sync pull --type ca_certificates --force

# Pull cryptographic keys and key sets from Konnect
ops kong sync pull --type key_sets --force
ops kong sync pull --type keys --force

# Pull vault configurations from Konnect (Enterprise)
ops kong sync pull --type vaults --force
```

#### `ops kong sync rollback`

Rollback a previous sync operation using the audit history.

```bash
# View sync history to find sync IDs
ops kong sync history

# Preview what would be rolled back (dry run)
ops kong sync rollback <sync-id> --dry-run

# Execute rollback
ops kong sync rollback <sync-id>

# Rollback without confirmation
ops kong sync rollback <sync-id> --force

# Rollback only specific entity type
ops kong sync rollback <sync-id> --type services
```

**Options:**

| Option      | Short | Description                             |
| ----------- | ----- | --------------------------------------- |
| `--dry-run` | `-n`  | Preview rollback without making changes |
| `--type`    | `-t`  | Only rollback specific entity type      |
| `--force`   | `-f`  | Execute without confirmation prompt     |

**Output (dry run):**

```text
Rollback Preview: abc12345...
Original sync: push (Konnect → Gateway)
Timestamp: 2026-01-23T10:30:00Z

┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┓
┃ Entity Type  ┃ Name             ┃ Action  ┃ Target  ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━┩
│ services     │ api-service      │ delete  │ konnect │
│ routes       │ api-route        │ delete  │ konnect │
│ services     │ updated-service  │ restore │ konnect │
└──────────────┴──────────────────┴─────────┴─────────┘

Dry run: Would rollback 3 operation(s)
```

**Rollback Actions:**

| Original Action | Rollback Action | Description                           |
| --------------- | --------------- | ------------------------------------- |
| `create`        | `delete`        | Deletes the entity that was created   |
| `update`        | `restore`       | Restores entity to its previous state |

**Workflow Example:**

```bash
# 1. Perform a sync push
ops kong sync push --type services --force

# 2. Realize the sync was incorrect, view history
ops kong sync history

# 3. Preview rollback
ops kong sync rollback abc12345... --dry-run

# 4. Execute rollback
ops kong sync rollback abc12345... --force

# 5. Verify entities were removed/restored
ops kong sync status --type services
```

**Limitations:**

- Cannot rollback dry-run syncs (no changes were made)
- Cannot rollback if `before_state` or `after_state` was not recorded
- Entities modified after the sync may need manual resolution

---

### Enterprise Features

Features available only with Kong Enterprise license.

#### `ops kong enterprise workspaces`

Manage Kong workspaces for multi-tenancy.

```bash
# List workspaces
ops kong enterprise workspaces list

# Get workspace details
ops kong enterprise workspaces get production

# Create a workspace
ops kong enterprise workspaces create production \
  --comment "Production environment" \
  --portal  # Enable Developer Portal

# Update a workspace
ops kong enterprise workspaces update production --comment "Updated description"

# Switch workspace context
ops kong enterprise workspaces use production

# Show current workspace
ops kong enterprise workspaces current

# Delete a workspace
ops kong enterprise workspaces delete staging
ops kong enterprise workspaces delete staging --force  # Skip confirmation
```

#### `ops kong enterprise rbac`

Manage Role-Based Access Control.

```bash
# List roles
ops kong enterprise rbac roles list

# Create a role
ops kong enterprise rbac roles create \
  --name api-developer \
  --comment "API developers with limited access"

# Add permissions to role
ops kong enterprise rbac roles add-permission api-developer \
  --endpoint "/services/*" \
  --actions read,create,update

# List users
ops kong enterprise rbac users list

# Create an admin user
ops kong enterprise rbac users create \
  --name "john.doe" \
  --email "john@example.com" \
  --role api-developer

# Assign role to user
ops kong enterprise rbac users assign-role john.doe admin
```

#### `ops kong enterprise vaults`

Manage secret vaults integration.

```bash
# List configured vaults
ops kong enterprise vaults list

# Get vault details
ops kong enterprise vaults get hashicorp-vault

# Configure HashiCorp Vault
ops kong enterprise vaults configure hcv \
  --name "hashicorp-vault" \
  --host "vault.example.com" \
  --port 8200 \
  --protocol https \
  --token "${VAULT_TOKEN}" \
  --mount "secret" \
  --kv-version 2

# Configure AWS Secrets Manager
ops kong enterprise vaults configure aws \
  --name "aws-secrets" \
  --region "us-east-1"

# Configure environment variables vault
ops kong enterprise vaults configure env \
  --name "env-vault" \
  --prefix "KONG_SECRET_"

# Delete a vault
ops kong enterprise vaults delete hashicorp-vault
ops kong enterprise vaults delete hashicorp-vault --force  # Skip confirmation

# Reference secrets in plugin config
ops kong plugins enable key-auth \
  --service payment-api \
  --config key_names={vault://hashicorp-vault/api-keys/payment}
```

#### `ops kong enterprise portal`

Manage Developer Portal.

```bash
# Show portal status
ops kong enterprise portal status
```

##### API Specifications

```bash
# List published specs
ops kong enterprise portal specs list

# Get specification details
ops kong enterprise portal specs get /payment-api

# Show spec contents
ops kong enterprise portal specs get /payment-api --contents

# Publish OpenAPI spec
ops kong enterprise portal specs publish ./openapi.yaml \
  --name "payment-api" \
  --path "/payment-api"

# Update an existing spec
ops kong enterprise portal specs update /payment-api ./openapi-v2.yaml

# Delete a spec
ops kong enterprise portal specs delete /payment-api
ops kong enterprise portal specs delete /payment-api --force
```

##### Developer Management

```bash
# List developers
ops kong enterprise portal developers list
ops kong enterprise portal developers list --status pending

# Get developer details
ops kong enterprise portal developers get dev@example.com

# Approve a pending developer
ops kong enterprise portal developers approve dev@example.com

# Reject a pending developer
ops kong enterprise portal developers reject dev@example.com

# Revoke access from an approved developer
ops kong enterprise portal developers revoke dev@example.com

# Delete a developer
ops kong enterprise portal developers delete dev@example.com
ops kong enterprise portal developers delete dev@example.com --force
```

---

## Common Workflows

### Setting Up a New API Service

Complete workflow for exposing a new backend API through Kong:

```bash
# 1. Create the service pointing to your backend
ops kong services create \
  --name payment-api \
  --host payment.internal.example.com \
  --port 8080 \
  --protocol http \
  --path /api/v1 \
  --tag production

# 2. Create a route to expose the service
ops kong routes create \
  --name payment-public-route \
  --service payment-api \
  --path /payments \
  --method GET \
  --method POST \
  --method PUT \
  --host api.example.com \
  --strip-path

# 3. Add rate limiting
ops kong plugins enable rate-limiting \
  --service payment-api \
  --config minute=100 \
  --config hour=5000

# 4. Require API key authentication
ops kong plugins enable key-auth \
  --service payment-api

# 5. Create a consumer and API key
ops kong consumers create --username mobile-app
ops kong consumers credentials add mobile-app \
  --type key-auth \
  --key "$YOUR_API_KEY"

# 6. Test the endpoint
curl -H "apikey: $YOUR_API_KEY" https://api.example.com/payments
```

### Adding Authentication to an Existing API

```bash
# Enable JWT authentication on the service
ops kong security jwt enable \
  --service payment-api \
  --claims-to-verify exp

# Add JWT credential for the consumer
ops kong security jwt add-credential mobile-app \
  --key "mobile-app-key" \
  --algorithm HS256 \
  --secret "$JWT_SECRET"

# Optionally, add ACL for group-based access control
ops kong security acl enable \
  --service payment-api \
  --allow premium-users,admin

# Add consumer to allowed group
ops kong security acl add-group mobile-app premium-users
```

### Configuring Rate Limiting by Consumer Tier

```bash
# Global rate limit (fallback)
ops kong traffic rate-limit enable \
  --service payment-api \
  --minute 60 \
  --limit-by consumer

# Higher limits for premium consumers (using consumer-specific plugin)
ops kong plugins enable rate-limiting \
  --consumer premium-user-1 \
  --service payment-api \
  --config minute=1000 \
  --config hour=50000
```

### Setting Up Load Balancing with Health Checks

```bash
# 1. Create an upstream for load balancing
ops kong upstreams create \
  --name payment-cluster \
  --algorithm round-robin

# 2. Add backend servers as targets
ops kong upstreams targets add payment-cluster --target 192.168.1.10:8080 --weight 100
ops kong upstreams targets add payment-cluster --target 192.168.1.11:8080 --weight 100
ops kong upstreams targets add payment-cluster --target 192.168.1.12:8080 --weight 50

# 3. Configure health checks
ops kong observability health set payment-cluster \
  --active-type http \
  --active-http-path /health \
  --active-interval-healthy 10 \
  --active-interval-unhealthy 5 \
  --active-successes-healthy 2 \
  --active-failures-unhealthy 3

# 4. Point service to the upstream
ops kong services update payment-api --host payment-cluster
```

### Exporting and Applying Declarative Config

```bash
# Export current configuration
ops kong config export production-config.yaml

# Edit the configuration file as needed
vim production-config.yaml

# Validate the updated configuration
ops kong config validate production-config.yaml

# Show differences before applying
ops kong config diff production-config.yaml

# Apply to Kong (DB-less mode)
ops kong config apply production-config.yaml --confirm
```

### Synchronizing TLS Certificates and Keys

Complete workflow for syncing certificate-related entities between Gateway and Konnect:

```bash
# 1. Check current sync status for TLS entities
ops kong sync status --type certificates
ops kong sync status --type snis
ops kong sync status --type ca_certificates

# 2. Preview what would be pushed (dry run)
ops kong sync push --type certificates --dry-run

# 3. Push certificates from Gateway to Konnect
ops kong sync push --type certificates --force

# 4. Push SNIs (must be after certificates due to dependency)
ops kong sync push --type snis --force

# 5. Push CA certificates for mTLS
ops kong sync push --type ca_certificates --force

# 6. Push cryptographic key sets and keys
ops kong sync push --type key_sets --force
ops kong sync push --type keys --force

# 7. Verify sync status
ops kong sync status --type certificates
ops kong sync status --type key_sets
```

**Pull certificates from Konnect to Gateway:**

```bash
# Preview what would be pulled
ops kong sync pull --type certificates --dry-run

# Pull all certificate types from Konnect
ops kong sync pull --type certificates --force
ops kong sync pull --type snis --force
ops kong sync pull --type ca_certificates --force

# Pull keys and key sets
ops kong sync pull --type key_sets --force
ops kong sync pull --type keys --force
```

**Note:** When syncing SNIs and Keys, ensure their parent entities (Certificates and
Key Sets) are synced first due to reference dependencies.

---

### Resolving Sync Conflicts Interactively

When entities have different configurations on Gateway and Konnect, use interactive
mode to resolve conflicts through the TUI:

```bash
# 1. Check for drift
ops kong sync status

# 2. If drift detected, launch interactive conflict resolution
ops kong sync push --interactive

# 3. In the TUI:
#    - Navigate conflicts with arrow keys or j/k
#    - Press Enter to view conflict details
#    - Press 's' to keep source (Gateway) values
#    - Press 't' to keep target (Konnect) values
#    - Press 'm' to merge (if available)
#    - Press 'k' to skip
#    - Press 'a' to review and apply all resolutions

# 4. Verify sync completed
ops kong sync status
```

**Batch Resolution Example:**

```bash
# Start interactive push
ops kong sync push --interactive

# In TUI: Press 's' to apply "Keep Source" to all pending conflicts
# Then press 'a' to apply, Enter to confirm
```

**Skip Conflicts in CI/CD:**

```bash
# When interactive isn't possible, skip conflicts and sync only clean entities
ops kong sync push --skip-conflicts --force
```

For detailed TUI documentation, see [Interactive Conflict Resolution](./conflict-resolution.md).

---

### Managing Consumer Credentials

```bash
# Create a consumer
ops kong consumers create \
  --username mobile-app \
  --custom-id app-12345 \
  --tag mobile

# Add multiple credential types
ops kong consumers credentials add mobile-app --type key-auth --key "api-key-1"
ops kong consumers credentials add mobile-app --type key-auth --key "api-key-2"
ops kong consumers credentials add mobile-app --type jwt --key "jwt-key" --algorithm HS256 --secret "$JWT_SECRET"

# List all credentials
ops kong consumers credentials list mobile-app

# Revoke a specific credential
ops kong consumers credentials delete mobile-app api-key-1-id
```

---

## Kong Feature Reference

### Available Authentication Plugins

| Plugin           | Description                   | Use Case                      |
| ---------------- | ----------------------------- | ----------------------------- |
| `key-auth`       | API key authentication        | Simple API access control     |
| `jwt`            | JSON Web Token validation     | Stateless authentication      |
| `oauth2`         | OAuth 2.0 authorization       | Third-party app authorization |
| `basic-auth`     | HTTP Basic authentication     | Simple username/password      |
| `hmac-auth`      | HMAC signature validation     | Secure API signing            |
| `ldap-auth`      | LDAP directory authentication | Enterprise user directories   |
| `openid-connect` | OpenID Connect (Enterprise)   | SSO integration               |

### Traffic Control Plugins

| Plugin                  | Description         | Key Settings                            |
| ----------------------- | ------------------- | --------------------------------------- |
| `rate-limiting`         | Request rate limits | minute, hour, policy, limit_by          |
| `request-size-limiting` | Payload size limits | allowed_payload_size, size_unit         |
| `request-termination`   | Block requests      | status_code, message                    |
| `proxy-cache`           | Response caching    | content_type, cache_ttl, strategy       |
| `request-transformer`   | Modify requests     | add/remove/rename headers, querystrings |
| `response-transformer`  | Modify responses    | add/remove headers, json body           |

### Security Plugins

| Plugin           | Description           | Key Settings                           |
| ---------------- | --------------------- | -------------------------------------- |
| `acl`            | Access control lists  | allow, deny (group names)              |
| `ip-restriction` | IP allowlist/denylist | allow, deny (CIDRs)                    |
| `cors`           | Cross-origin requests | origins, methods, headers, credentials |
| `bot-detection`  | Block bots            | allow, deny (user-agent patterns)      |
| `mtls-auth`      | Mutual TLS            | ca_certificates, skip_consumer_lookup  |

### Observability Plugins

| Plugin          | Description           | Key Settings                        |
| --------------- | --------------------- | ----------------------------------- |
| `prometheus`    | Prometheus metrics    | per_consumer, status_code_metrics   |
| `file-log`      | File logging          | path, reopen                        |
| `http-log`      | HTTP logging          | http_endpoint, method, content_type |
| `tcp-log`       | TCP logging           | host, port, tls                     |
| `syslog`        | Syslog logging        | host, port, facility, severity      |
| `opentelemetry` | OpenTelemetry tracing | endpoint, resource_attributes       |
| `zipkin`        | Zipkin tracing        | http_endpoint, sample_ratio         |

### Health Check Configuration

| Setting                           | Description                      | Default      |
| --------------------------------- | -------------------------------- | ------------ |
| `active.type`                     | Check type (http, https, tcp)    | http         |
| `active.http_path`                | Health endpoint path             | /            |
| `active.timeout`                  | Check timeout (seconds)          | 1            |
| `active.concurrency`              | Concurrent checks                | 10           |
| `active.healthy.interval`         | Healthy check interval           | 0 (disabled) |
| `active.healthy.successes`        | Successes to mark healthy        | 0            |
| `active.unhealthy.interval`       | Unhealthy check interval         | 0 (disabled) |
| `active.unhealthy.http_failures`  | Failures to mark unhealthy       | 0            |
| `passive.healthy.successes`       | Proxy successes to mark healthy  | 0            |
| `passive.unhealthy.http_failures` | Proxy failures to mark unhealthy | 0            |
| `passive.unhealthy.timeouts`      | Proxy timeouts to mark unhealthy | 0            |

---

## Troubleshooting

### Connection Issues

```bash
# Test Admin API connectivity
ops kong status --verbose

# Check with curl
curl -i http://localhost:8001/status
```

### DB-less Mode Restrictions

In DB-less mode, the following operations are read-only:

- All entity creation (services, routes, consumers, upstreams)
- Plugin configuration
- Credential management
- Certificate management

Use `ops kong config apply <file>` to modify configuration.

### Common Error Messages

| Error                        | Cause                           | Solution                            |
| ---------------------------- | ------------------------------- | ----------------------------------- |
| `KONG_ADMIN_API_UNREACHABLE` | Cannot connect to Admin API     | Check URL, network, and Kong status |
| `KONG_AUTH_FAILED`           | Authentication rejected         | Verify API key or certificates      |
| `KONG_DBLESS_WRITE_DENIED`   | Write operation in DB-less mode | Use declarative config instead      |
| `KONG_ENTITY_NOT_FOUND`      | Entity doesn't exist            | Verify entity name/ID               |
| `KONG_SCHEMA_VIOLATION`      | Invalid configuration           | Check required fields and types     |

### Debug Mode

```bash
# Enable verbose output
ops kong --verbose services list

# Output as JSON for debugging
ops kong services get payment-api --output json
```

---

## Related Documentation

- [Interactive Conflict Resolution](./conflict-resolution.md) - TUI for resolving sync conflicts
- [History and Rollback](../features/history-rollback.md) - Sync history and rollback features
- [Dry Run Mode](../features/dry-run-mode.md) - Preview changes before applying
- [Plugin Development Guide](development.md)
- [Hot Loading](hot-loading.md)
- [Available Plugins](available-plugins.md)
- [Kong Official Documentation](https://docs.konghq.com/)
