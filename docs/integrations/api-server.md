# API Server Integration

REST API server mode for programmatic access to System Control CLI functionality, enabling
integration with other tools and automated workflows.

## Overview

API server features:

- **RESTful API**: Complete HTTP API coverage of CLI functionality
- **Authentication & Authorization**: Multiple auth methods and role-based access
- **Real-time Updates**: WebSocket support for live updates and streaming
- **OpenAPI Documentation**: Auto-generated API documentation
- **Rate Limiting**: Configurable rate limiting and throttling
- **Audit Logging**: Comprehensive API access and change tracking

## Configuration

### Basic API Server Setup

```yaml
# integrations/api-server.yaml
api_server:
  enabled: true

  server:
    host: "0.0.0.0"
    port: 8080
    workers: 4

  tls:
    enabled: true
    cert_file: "/etc/ssl/certs/system-control-api.pem"
    key_file: "/etc/ssl/private/system-control-api.key"
    ca_file: "/etc/ssl/certs/ca.pem"

  cors:
    enabled: true
    allowed_origins:
      - "https://dashboard.company.com"
      - "https://admin.company.com"
    allowed_methods: ["GET", "POST", "PUT", "DELETE", "PATCH"]
    allowed_headers: ["Authorization", "Content-Type", "X-Request-ID"]

  rate_limiting:
    enabled: true
    requests_per_minute: 100
    burst_size: 20

  authentication:
    enabled: true
    methods: ["jwt", "api_key", "basic"]

  authorization:
    enabled: true
    rbac: true

  monitoring:
    metrics: true
    health_checks: true

  documentation:
    openapi: true
    swagger_ui: true
    redoc: true
```

### Authentication Configuration

```yaml
# auth/api-auth.yaml
authentication:
  jwt:
    enabled: true
    secret_env: "JWT_SECRET"
    algorithm: "HS256"
    expiration: "24h"
    issuer: "system-control-api"

    # OIDC integration
    oidc:
      enabled: true
      provider_url: "https://auth.company.com"
      client_id_env: "OIDC_CLIENT_ID"
      client_secret_env: "OIDC_CLIENT_SECRET"

  api_key:
    enabled: true
    header_name: "X-API-Key"
    storage: "database" # or "redis", "file"

  basic_auth:
    enabled: true
    users:
      - username: "admin"
        password_hash: "$2b$12$..."
        roles: ["admin"]
      - username: "readonly"
        password_hash: "$2b$12$..."
        roles: ["viewer"]

  service_accounts:
    enabled: true
    token_rotation: "30d"
    scopes: ["deployment", "monitoring", "configuration"]
```

### Authorization & RBAC

```yaml
# auth/rbac.yaml
rbac:
  roles:
    admin:
      description: "Full administrative access"
      permissions:
        - "*"

    deployer:
      description: "Deployment and service management"
      permissions:
        - "services:read"
        - "services:write"
        - "deployments:*"
        - "configurations:read"
        - "monitoring:read"

    operator:
      description: "Operations and monitoring"
      permissions:
        - "services:read"
        - "monitoring:*"
        - "logs:read"
        - "metrics:read"
        - "health:read"

    viewer:
      description: "Read-only access"
      permissions:
        - "services:read"
        - "monitoring:read"
        - "configurations:read"

  policies:
    environment_restrictions:
      production:
        required_roles: ["admin", "deployer"]
        require_approval: true

      staging:
        required_roles: ["admin", "deployer", "operator"]

      development:
        required_roles: ["*"]

    resource_limits:
      max_parallel_deployments: 3
      deployment_timeout: "30m"
      max_log_query_range: "7d"
```

## Starting the API Server

### CLI Commands

```bash
# Start API server
sysctl api-server start --config api-server.yaml

# Start with specific configuration
sysctl api-server start --host 0.0.0.0 --port 8080 --workers 4

# Start in development mode
sysctl api-server start --dev --auto-reload

# Generate API documentation
sysctl api-server docs generate --output api-docs.html

# Test API server
sysctl api-server test --endpoint http://localhost:8080/health
```

### Systemd Service

```ini
# /etc/systemd/system/system-control-api.service
[Unit]
Description=System Control API Server
After=network.target
Wants=network.target

[Service]
Type=exec
User=system-control
Group=system-control
WorkingDirectory=/opt/system-control
ExecStart=/usr/local/bin/sysctl api-server start --config /etc/system-control/api-server.yaml
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=system-control-api

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/var/lib/system-control /var/log/system-control

[Install]
WantedBy=multi-user.target
```

## API Endpoints

### Service Management

```bash
# List services
curl -H "Authorization: Bearer ${TOKEN}" \
  http://api.company.com/api/v1/services

# Get service details
curl -H "Authorization: Bearer ${TOKEN}" \
  http://api.company.com/api/v1/services/api

# Deploy service
curl -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"image": "api:v2.1.0", "environment": "production"}' \
  http://api.company.com/api/v1/services/api/deploy

# Scale service
curl -X PUT \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"replicas": 5}' \
  http://api.company.com/api/v1/services/api/scale

# Service health
curl -H "Authorization: Bearer ${TOKEN}" \
  http://api.company.com/api/v1/services/api/health
```

### Deployment Management

```bash
# List deployments
curl -H "Authorization: Bearer ${TOKEN}" \
  http://api.company.com/api/v1/deployments

# Create deployment
curl -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "service": "api",
    "image": "api:v2.1.0",
    "environment": "production",
    "strategy": "blue-green"
  }' \
  http://api.company.com/api/v1/deployments

# Get deployment status
curl -H "Authorization: Bearer ${TOKEN}" \
  http://api.company.com/api/v1/deployments/dep-12345

# Rollback deployment
curl -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{"version": "v2.0.0"}' \
  http://api.company.com/api/v1/deployments/dep-12345/rollback
```

### Monitoring & Metrics

```bash
# Get system status
curl -H "Authorization: Bearer ${TOKEN}" \
  http://api.company.com/api/v1/status

# Query metrics
curl -H "Authorization: Bearer ${TOKEN}" \
  "http://api.company.com/api/v1/metrics?service=api&duration=1h"

# Get logs
curl -H "Authorization: Bearer ${TOKEN}" \
  "http://api.company.com/api/v1/logs?service=api&level=error&since=1h"

# Health checks
curl -H "Authorization: Bearer ${TOKEN}" \
  http://api.company.com/api/v1/health/api
```

## WebSocket Integration

### Real-time Updates

```javascript
// WebSocket connection for real-time updates
const ws = new WebSocket("wss://api.company.com/api/v1/ws")

// Authentication
ws.onopen = function () {
  ws.send(
    JSON.stringify({
      type: "auth",
      token: "your-jwt-token",
    })
  )
}

// Subscribe to service updates
ws.send(
  JSON.stringify({
    type: "subscribe",
    channel: "services",
    filters: {
      environment: "production",
    },
  })
)

// Handle messages
ws.onmessage = function (event) {
  const message = JSON.parse(event.data)

  switch (message.type) {
    case "service_update":
      console.log("Service updated:", message.data)
      break

    case "deployment_status":
      console.log("Deployment status:", message.data)
      break

    case "health_change":
      console.log("Health status changed:", message.data)
      break

    case "log_entry":
      console.log("New log entry:", message.data)
      break
  }
}
```

### WebSocket Channels

```yaml
# websocket/channels.yaml
websocket_channels:
  services:
    description: "Service status updates"
    events: ["created", "updated", "deleted", "health_changed"]
    filters: ["service", "environment", "status"]

  deployments:
    description: "Deployment progress updates"
    events: ["started", "progress", "completed", "failed", "rolled_back"]
    filters: ["service", "environment", "deployment_id"]

  metrics:
    description: "Real-time metrics streaming"
    events: ["metric_update"]
    filters: ["service", "metric_name"]
    rate_limit: "10/second"

  logs:
    description: "Real-time log streaming"
    events: ["log_entry"]
    filters: ["service", "level", "environment"]
    rate_limit: "100/second"

  alerts:
    description: "Alert notifications"
    events: ["alert_fired", "alert_resolved"]
    filters: ["severity", "service", "environment"]
```

## API Client Libraries

### Python Client

```python
# clients/python/system_operations_manager_client.py
import requests
import asyncio
import websockets
import json
from typing import Dict, List, Optional

class SystemControlClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        })

    def list_services(self, environment: Optional[str] = None) -> List[Dict]:
        params = {'environment': environment} if environment else {}
        response = self.session.get(f'{self.base_url}/api/v1/services', params=params)
        response.raise_for_status()
        return response.json()

    def deploy_service(self, service: str, image: str, environment: str, **kwargs) -> Dict:
        data = {
            'image': image,
            'environment': environment,
            **kwargs
        }
        response = self.session.post(f'{self.base_url}/api/v1/services/{service}/deploy', json=data)
        response.raise_for_status()
        return response.json()

    def get_service_health(self, service: str, environment: Optional[str] = None) -> Dict:
        params = {'environment': environment} if environment else {}
        response = self.session.get(f'{self.base_url}/api/v1/services/{service}/health', params=params)
        response.raise_for_status()
        return response.json()

    async def stream_logs(self, service: str, callback, **filters):
        uri = f"wss://{self.base_url.split('://', 1)[1]}/api/v1/ws"

        async with websockets.connect(uri) as websocket:
            # Authenticate
            await websocket.send(json.dumps({
                'type': 'auth',
                'token': self.token
            }))

            # Subscribe to logs
            await websocket.send(json.dumps({
                'type': 'subscribe',
                'channel': 'logs',
                'filters': {'service': service, **filters}
            }))

            # Handle messages
            async for message in websocket:
                data = json.loads(message)
                if data['type'] == 'log_entry':
                    callback(data['data'])

# Usage example
client = SystemControlClient('https://api.company.com', 'your-jwt-token')

# List services
services = client.list_services(environment='production')

# Deploy service
deployment = client.deploy_service('api', 'api:v2.1.0', 'production', strategy='blue-green')

# Stream logs
async def log_handler(log_entry):
    print(f"[{log_entry['timestamp']}] {log_entry['level']}: {log_entry['message']}")

asyncio.run(client.stream_logs('api', log_handler, level='error'))
```

### JavaScript Client

```javascript
// clients/javascript/system-control-client.js
class SystemControlClient {
  constructor(baseUrl, token) {
    this.baseUrl = baseUrl.replace(/\/$/, "")
    this.token = token
  }

  async _request(method, endpoint, data = null) {
    const url = `${this.baseUrl}/api/v1${endpoint}`
    const options = {
      method,
      headers: {
        Authorization: `Bearer ${this.token}`,
        "Content-Type": "application/json",
      },
    }

    if (data) {
      options.body = JSON.stringify(data)
    }

    const response = await fetch(url, options)

    if (!response.ok) {
      throw new Error(`API request failed: ${response.status} ${response.statusText}`)
    }

    return response.json()
  }

  async listServices(environment = null) {
    const params = environment ? `?environment=${environment}` : ""
    return this._request("GET", `/services${params}`)
  }

  async deployService(service, image, environment, options = {}) {
    const data = { image, environment, ...options }
    return this._request("POST", `/services/${service}/deploy`, data)
  }

  async getServiceHealth(service, environment = null) {
    const params = environment ? `?environment=${environment}` : ""
    return this._request("GET", `/services/${service}/health${params}`)
  }

  streamUpdates(channels, filters = {}) {
    const wsUrl = this.baseUrl.replace(/^http/, "ws") + "/api/v1/ws"
    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      // Authenticate
      ws.send(
        JSON.stringify({
          type: "auth",
          token: this.token,
        })
      )

      // Subscribe to channels
      channels.forEach(channel => {
        ws.send(
          JSON.stringify({
            type: "subscribe",
            channel,
            filters,
          })
        )
      })
    }

    return ws
  }
}

// Usage example
const client = new SystemControlClient("https://api.company.com", "your-jwt-token")

// List services
client.listServices("production").then(services => {
  console.log("Services:", services)
})

// Stream deployment updates
const ws = client.streamUpdates(["deployments"], { environment: "production" })
ws.onmessage = event => {
  const message = JSON.parse(event.data)
  if (message.type === "deployment_status") {
    console.log("Deployment update:", message.data)
  }
}
```

## API Documentation

### OpenAPI Specification

```yaml
# docs/openapi.yaml
openapi: 3.0.3
info:
  title: System Control API
  description: REST API for System Control CLI
  version: "2.1.0"
  contact:
    name: Platform Team
    email: platform@company.com
  license:
    name: MIT

servers:
  - url: https://api.company.com/api/v1
    description: Production server
  - url: https://staging-api.company.com/api/v1
    description: Staging server

security:
  - bearerAuth: []
  - apiKeyAuth: []

paths:
  /services:
    get:
      summary: List services
      tags: [Services]
      parameters:
        - name: environment
          in: query
          schema:
            type: string
            enum: [development, staging, production]
      responses:
        200:
          description: List of services
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: "#/components/schemas/Service"

  /services/{service}/deploy:
    post:
      summary: Deploy service
      tags: [Deployments]
      parameters:
        - name: service
          in: path
          required: true
          schema:
            type: string
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/DeploymentRequest"
      responses:
        202:
          description: Deployment started
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/Deployment"

components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
    apiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key

  schemas:
    Service:
      type: object
      properties:
        name:
          type: string
        status:
          type: string
          enum: [running, stopped, failed]
        replicas:
          type: object
          properties:
            desired:
              type: integer
            ready:
              type: integer
        health:
          type: string
          enum: [healthy, unhealthy, unknown]
        version:
          type: string
        environment:
          type: string
        last_deployed:
          type: string
          format: date-time

    DeploymentRequest:
      type: object
      required: [image, environment]
      properties:
        image:
          type: string
          example: "api:v2.1.0"
        environment:
          type: string
          enum: [development, staging, production]
        strategy:
          type: string
          enum: [rolling, blue-green, canary]
          default: rolling
        replicas:
          type: integer
          minimum: 1
          maximum: 100
        timeout:
          type: integer
          description: Deployment timeout in seconds
          default: 600

    Deployment:
      type: object
      properties:
        id:
          type: string
        service:
          type: string
        status:
          type: string
          enum: [pending, running, completed, failed, rolled_back]
        strategy:
          type: string
        created_at:
          type: string
          format: date-time
        completed_at:
          type: string
          format: date-time
```

## Monitoring and Observability

### API Metrics

```yaml
# monitoring/api-metrics.yaml
api_metrics:
  http_requests:
    - name: "http_requests_total"
      type: "counter"
      description: "Total HTTP requests"
      labels: ["method", "endpoint", "status_code"]

    - name: "http_request_duration_seconds"
      type: "histogram"
      description: "HTTP request duration"
      labels: ["method", "endpoint"]
      buckets: [0.1, 0.5, 1.0, 2.5, 5.0, 10.0]

  authentication:
    - name: "auth_attempts_total"
      type: "counter"
      description: "Authentication attempts"
      labels: ["method", "status"]

    - name: "active_sessions"
      type: "gauge"
      description: "Number of active sessions"

  websockets:
    - name: "websocket_connections"
      type: "gauge"
      description: "Active WebSocket connections"

    - name: "websocket_messages_total"
      type: "counter"
      description: "WebSocket messages sent"
      labels: ["channel", "type"]

  rate_limiting:
    - name: "rate_limit_hits_total"
      type: "counter"
      description: "Rate limit violations"
      labels: ["endpoint", "client"]
```

### Health Checks

```bash
# Health check endpoints
curl http://api.company.com/health
# Returns: {"status": "healthy", "timestamp": "2024-01-15T10:30:00Z"}

curl http://api.company.com/health/detailed
# Returns detailed health information including dependencies

curl http://api.company.com/metrics
# Returns Prometheus metrics

curl http://api.company.com/ready
# Returns readiness status for load balancers
```

## Security Best Practices

### API Security Configuration

```yaml
# security/api-security.yaml
security:
  headers:
    - name: "X-Content-Type-Options"
      value: "nosniff"
    - name: "X-Frame-Options"
      value: "DENY"
    - name: "X-XSS-Protection"
      value: "1; mode=block"
    - name: "Strict-Transport-Security"
      value: "max-age=31536000; includeSubDomains"

  input_validation:
    max_request_size: "10MB"
    timeout: "30s"
    sanitize_input: true

  audit_logging:
    enabled: true
    events: ["auth", "deployment", "config_change", "access_denied"]
    storage: "elasticsearch"

  ip_filtering:
    enabled: true
    allowed_ranges:
      - "10.0.0.0/8"
      - "192.168.0.0/16"
    blocked_ranges:
      - "192.168.100.0/24" # Known malicious range
```

## Troubleshooting

### Common Issues

```bash
# Test API connectivity
curl -I http://api.company.com/health

# Debug authentication
curl -H "Authorization: Bearer ${TOKEN}" -v http://api.company.com/api/v1/services

# Check API server logs
sysctl api-server logs --level error --tail 100

# Validate API configuration
sysctl api-server validate-config --file api-server.yaml

# Performance analysis
sysctl api-server analyze performance --duration 1h
```

### Performance Optimization

```bash
# Analyze slow endpoints
sysctl api-server analyze slow-endpoints --threshold 1s --duration 24h

# Cache performance
sysctl api-server analyze cache-performance

# Connection pool optimization
sysctl api-server optimize connection-pools

# Rate limiting analysis
sysctl api-server analyze rate-limiting --top-clients 20
```
