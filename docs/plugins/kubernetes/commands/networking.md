# Kubernetes Plugin > Commands > Networking

[< Back to Index](../index.md) | [Commands](./) | [Ecosystem](../ecosystem/) | [TUI](../tui.md) | [Examples](../examples.md)

---

## Table of Contents

- [Overview](#overview)
- [Common Options](#common-options)
- [Service Commands](#service-commands)
  - [ops k8s services list](#ops-k8s-services-list)
  - [ops k8s services get](#ops-k8s-services-get)
  - [ops k8s services create](#ops-k8s-services-create)
  - [ops k8s services update](#ops-k8s-services-update)
  - [ops k8s services delete](#ops-k8s-services-delete)
- [Ingress Commands](#ingress-commands)
  - [ops k8s ingresses list](#ops-k8s-ingresses-list)
  - [ops k8s ingresses get](#ops-k8s-ingresses-get)
  - [ops k8s ingresses create](#ops-k8s-ingresses-create)
  - [ops k8s ingresses update](#ops-k8s-ingresses-update)
  - [ops k8s ingresses delete](#ops-k8s-ingresses-delete)
- [Network Policy Commands](#network-policy-commands)
  - [ops k8s network-policies list](#ops-k8s-network-policies-list)
  - [ops k8s network-policies get](#ops-k8s-network-policies-get)
  - [ops k8s network-policies create](#ops-k8s-network-policies-create)
  - [ops k8s network-policies delete](#ops-k8s-network-policies-delete)
- [Troubleshooting](#troubleshooting)
- [See Also](#see-also)

---

## Overview

Networking commands manage Kubernetes networking resources including Services, Ingresses, and Network Policies. These
resources enable communication between pods and external clients, and provide security controls for network traffic.

---

## Common Options

Common options are shared across all networking commands:

| Option             | Short | Type    | Default        | Description                                    |
| ------------------ | ----- | ------- | -------------- | ---------------------------------------------- |
| `--output`         | `-o`  | string  | `table`        | Output format: `table`, `json`, or `yaml`      |
| `--namespace`      | `-n`  | string  | config default | Target Kubernetes namespace                    |
| `--all-namespaces` | `-A`  | boolean | false          | List resources across all namespaces           |
| `--selector`       | `-l`  | string  | -              | Label selector for filtering (e.g., `app=web`) |
| `--force`          | `-f`  | boolean | false          | Skip confirmation prompts                      |

---

## Service Commands

Services expose applications running on pods, providing stable network endpoints and load balancing.

### `ops k8s services list`

List all services in a namespace or across all namespaces.

This command displays services with their type, cluster IP, external IP (if any), and port information.

**Usage:**

```bash
ops k8s services list
ops k8s services list -n production
ops k8s services list --all-namespaces
ops k8s services list -A
ops k8s services list -l app=web
ops k8s services list --output json
```

**Options:**

| Option             | Short | Type    | Default        | Description                               |
| ------------------ | ----- | ------- | -------------- | ----------------------------------------- |
| `--namespace`      | `-n`  | string  | config default | Target namespace                          |
| `--all-namespaces` | `-A`  | boolean | false          | List across all namespaces                |
| `--selector`       | `-l`  | string  | -              | Label selector to filter services         |
| `--output`         | `-o`  | string  | `table`        | Output format: `table`, `json`, or `yaml` |

**Example Output (Table):**

```text
┏━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━┳━━━━━┓
┃ Name        ┃ Namespace ┃ Type         ┃ Cluster-IP ┃ External-IP ┃ Ports ┃ Age ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━╇━━━━━┩
│ kubernetes  │ default   │ ClusterIP    │ 10.0.0.1   │ <none>      │ 443   │ 1y  │
│ nginx       │ default   │ ClusterIP    │ 10.0.1.5   │ <none>      │ 80    │ 30d │
│ web-api     │ default   │ LoadBalancer │ 10.0.1.10  │ 34.56.78.90 │ 80    │ 15d │
│ db-internal │ default   │ ClusterIP    │ 10.0.1.20  │ <none>      │ 5432  │ 7d  │
└─────────────┴───────────┴──────────────┴────────────┴─────────────┴───────┴─────┘
```

**Service Types:**

| Type         | Purpose                | External Access                    |
| ------------ | ---------------------- | ---------------------------------- |
| ClusterIP    | Default; internal only | Pod to pod within cluster          |
| NodePort     | Expose on node ports   | `<NodeIP>:<NodePort>`              |
| LoadBalancer | Cloud load balancer    | Cloud provider assigns external IP |
| ExternalName | DNS CNAME              | External service by DNS name       |

**Filter Examples:**

```bash
# List services by label
ops k8s services list -l app=web

# List services in specific namespace
ops k8s services list -n production

# List all LoadBalancer services
ops k8s services list --all-namespaces | grep LoadBalancer

# List services in JSON format
ops k8s services list --output json
```

**Notes:**

- Cluster-IP is internal to the cluster and not accessible externally
- External-IP shown only for LoadBalancer services with cloud integration
- Ports column shows service port(s), not target container ports
- Services use selectors to route traffic to matching pods

---

### `ops k8s services get`

Get detailed information about a specific service.

This command displays comprehensive service configuration including selector labels, port mappings, and status.

**Usage:**

```bash
ops k8s services get my-service
ops k8s services get web -n production
ops k8s services get api --output json
ops k8s services get db-internal -o yaml
```

**Arguments:**

| Argument | Type   | Description                    |
| -------- | ------ | ------------------------------ |
| `name`   | string | Name of the service (required) |

**Options:**

| Option        | Short | Type   | Default        | Description                               |
| ------------- | ----- | ------ | -------------- | ----------------------------------------- |
| `--namespace` | `-n`  | string | config default | Namespace containing service              |
| `--output`    | `-o`  | string | `table`        | Output format: `table`, `json`, or `yaml` |

**Example Output (Table):**

```text
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Property         ┃ Value        ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ Name             │ web-api      │
│ Namespace        │ default      │
│ Type             │ LoadBalancer │
│ Cluster IP       │ 10.0.1.10    │
│ External IP      │ 34.56.78.90  │
│ Ports            │ 80:30080/TCP │
│ Selector         │ app: web     │
│                  │ version: 1   │
│ Session Affinity │ None         │
│ Age              │ 15d          │
└──────────────────┴──────────────┘
```

**Example Output (YAML):**

```yaml
service:
  name: web-api
  namespace: default
  type: LoadBalancer
  clusterIP: 10.0.1.10
  externalIP: 34.56.78.90
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8080
      nodePort: 30080
  selector:
    app: web
    version: "1"
  sessionAffinity: None
  age: 15d
```

**Notes:**

- Selector shows which pods this service routes traffic to
- Multiple ports can be defined for a single service
- Session affinity controls client IP-based routing
- External IP is only for LoadBalancer type

---

### `ops k8s services create`

Create a new service to expose pods.

This command creates a service with specified type, port mappings, and pod selectors.

**Usage:**

```bash
ops k8s services create my-svc --type ClusterIP --port 80:8080/TCP --selector app=web
ops k8s services create web-api --type LoadBalancer --selector app=web --port 80:8080/TCP
ops k8s services create db-internal --type ClusterIP --selector app=postgres --port 5432:5432/TCP
ops k8s services create external --type ExternalName --selector app=legacy
```

**Arguments:**

| Argument | Type   | Description                     |
| -------- | ------ | ------------------------------- |
| `name`   | string | Name for the service (required) |

**Options:**

| Option        | Short | Type        | Default        | Description                                        |
| ------------- | ----- | ----------- | -------------- | -------------------------------------------------- |
| `--type`      | `-t`  | string      | `ClusterIP`    | Service type: ClusterIP, NodePort, or              |
| `--namespace` | `-n`  | string      | config default | Target namespace                                   |
| `--selector`  | `-s`  | string list | -              | Pod selectors in key=value format                  |
| `--port`      | `-p`  | string list | -              | Port mappings in format `port:targetPort/protocol` |
| `--label`     | `-l`  | string list | -              | Service labels in key=value format                 |
| `--output`    | `-o`  | string      | `table`        | Output format                                      |

**Port Specification Format:**

```text
port:targetPort/protocol

port        - Service port (exposed to clients)
targetPort  - Pod container port
protocol    - TCP or UDP (default: TCP)

Examples:
- 80:8080/TCP              # Service port 80 → container port 8080
- 443:443/TLS              # HTTPS service
- 53:53/UDP                # DNS service
- 80:80/TCP                # Same port on both sides
```

**Service Creation Examples:**

```bash
# ClusterIP service (internal only)
ops k8s services create web --type ClusterIP \
  --selector app=web \
  --port 80:8080/TCP

# LoadBalancer service (external access)
ops k8s services create api --type LoadBalancer \
  --selector app=api,version=v2 \
  --port 443:8443/TCP \
  --port 80:8080/TCP

# Database service
ops k8s services create postgres --type ClusterIP \
  --selector app=postgres \
  --port 5432:5432/TCP

# Service with labels
ops k8s services create cache --type ClusterIP \
  --selector app=redis \
  --port 6379:6379/TCP \
  -l app=cache \
  -l tier=backend \
  -l env=production
```

**Example Output:**

```text
Created Service: web-api

┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Property   ┃ Value        ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ Name       │ web-api      │
│ Type       │ LoadBalancer │
│ Cluster IP │ 10.0.1.100   │
│ Ports      │ 80:8080/TCP  │
│ Selector   │ app: web     │
└────────────┴──────────────┘
```

**Selector Matching:**

```bash
# Service routes to pods with BOTH labels
ops k8s services create myservice \
  --selector app=web,env=production

# Service routes to pods with matching label
ops k8s services create simple \
  --selector app=web
```

**Notes:**

- Selectors must match pod labels exactly
- Multiple port mappings supported
- Service name becomes DNS name within cluster
- Creating service doesn't create backing pods; ensure pods exist

---

### `ops k8s services update`

Update an existing service.

This command updates service configuration including type, port mappings, and selectors.

**Usage:**

```bash
ops k8s services update my-svc --type LoadBalancer
ops k8s services update web --selector app=web,version=2
ops k8s services update api --port 443:8443/TCP
ops k8s services update db -n data --type ClusterIP
```

**Arguments:**

| Argument | Type   | Description                    |
| -------- | ------ | ------------------------------ |
| `name`   | string | Name of the service (required) |

**Options:**

| Option        | Short | Type        | Default        | Description                    |
| ------------- | ----- | ----------- | -------------- | ------------------------------ |
| `--namespace` | `-n`  | string      | config default | Namespace containing service   |
| `--type`      | `-t`  | string      | -              | New service type               |
| `--selector`  | `-s`  | string list | -              | New pod selectors (repeatable) |
| `--port`      | `-p`  | string list | -              | New port mappings (repeatable) |
| `--output`    | `-o`  | string      | `table`        | Output format                  |

**Update Examples:**

```bash
# Change service type
ops k8s services update web --type LoadBalancer

# Update selector labels
ops k8s services update api --selector app=api,version=2

# Update port mappings
ops k8s services update https-svc --port 443:8443/TCP

# Update in specific namespace
ops k8s services update internal-db -n backend --selector app=postgres
```

**Example Output:**

```text
Updated Service: web-api

┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Property   ┃ Value        ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ Name       │ web-api      │
│ Type       │ LoadBalancer │
│ Cluster IP │ 10.0.1.100   │
│ Ports      │ 80:8080/TCP  │
│ Selector   │ app: web     │
└────────────┴──────────────┘
```

**Notes:**

- Service IP remains the same after update
- Selector changes immediately affect traffic routing
- Type changes may affect external accessibility

---

### `ops k8s services delete`

Delete a service.

This command deletes a service, preventing access to the pods it was exposing.

**Usage:**

```bash
ops k8s services delete my-service
ops k8s services delete web -n production
ops k8s services delete api --force
```

**Arguments:**

| Argument | Type   | Description                              |
| -------- | ------ | ---------------------------------------- |
| `name`   | string | Name of the service to delete (required) |

**Options:**

| Option        | Short | Type    | Default        | Description                  |
| ------------- | ----- | ------- | -------------- | ---------------------------- |
| `--namespace` | `-n`  | string  | config default | Namespace containing service |
| `--force`     | `-f`  | boolean | false          | Skip confirmation            |

**Example Output:**

```text
Are you sure you want to delete service 'web' in namespace 'default'? [y/N]: y
Service 'web' deleted
```

**Warnings:**

- Clients connecting through this service will lose connectivity
- Pods are not deleted, only the service endpoint
- Load balancer will be deprovisioned if it exists

**Notes:**

- Service deletion is immediate
- DNS name becomes unreachable
- Consider traffic impact before deleting

---

## Ingress Commands

Ingresses provide HTTP/HTTPS routing to services based on hostnames and paths. They are the recommended way to expose
HTTP services externally.

### `ops k8s ingresses list`

List all ingresses in a namespace.

This command displays ingresses with their associated hosts, addresses, and configuration.

**Usage:**

```bash
ops k8s ingresses list
ops k8s ingresses list -n production
ops k8s ingresses list --all-namespaces
ops k8s ingresses list -A
ops k8s ingresses list --output json
```

**Options:**

| Option             | Short | Type    | Default        | Description                |
| ------------------ | ----- | ------- | -------------- | -------------------------- |
| `--namespace`      | `-n`  | string  | config default | Target namespace           |
| `--all-namespaces` | `-A`  | boolean | false          | List across all namespaces |
| `--selector`       | `-l`  | string  | -              | Label selector to filter   |
| `--output`         | `-o`  | string  | `table`        | Output format              |

**Example Output (Table):**

```text
┏━━━━━━━┳━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━┓
┃ Name  ┃ Namespace ┃ Class ┃ Hosts           ┃ Addresses  ┃ Age ┃
┡━━━━━━━╇━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━┩
│ web   │ default   │ nginx │ example.com     │ 34.56.78.1 │ 30d │
│ api   │ default   │ nginx │ api.example.com │ 34.56.78.1 │ 15d │
│ admin │ default   │ nginx │ admin.prod      │ pending    │ 2d  │
└───────┴───────────┴───────┴─────────────────┴────────────┴─────┘
```

**Ingress Class:**

| Class | Controller   | Purpose                        |
| ----- | ------------ | ------------------------------ |
| nginx | NGINX        | Open-source ingress controller |
| gce   | Google Cloud | Google Cloud Load Balancer     |
| awslb | AWS          | AWS Application Load Balancer  |

**Notes:**

- Addresses shows assigned load balancer IP
- Pending means load balancer is still being provisioned
- Multiple hosts can be routed in one ingress
- Requires ingress controller to be running

---

### `ops k8s ingresses get`

Get detailed information about an ingress.

This command displays the complete ingress configuration including rules, TLS settings, and routing details.

**Usage:**

```bash
ops k8s ingresses get my-ingress
ops k8s ingresses get web -n production
ops k8s ingresses get api --output json
ops k8s ingresses get admin -o yaml
```

**Arguments:**

| Argument | Type   | Description                    |
| -------- | ------ | ------------------------------ |
| `name`   | string | Name of the ingress (required) |

**Options:**

| Option        | Short | Type   | Default        | Description                  |
| ------------- | ----- | ------ | -------------- | ---------------------------- |
| `--namespace` | `-n`  | string | config default | Namespace containing ingress |
| `--output`    | `-o`  | string | `table`        | Output format                |

**Example Output (Table):**

```text
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Property      ┃ Value       ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ Name          │ web         │
│ Namespace     │ default     │
│ Ingress Class │ nginx       │
│ Hosts         │ example.com │
│ Address       │ 34.56.78.1  │
│ Rules         │ 1           │
│ TLS Enabled   │ Yes         │
│ Age           │ 30d         │
└───────────────┴─────────────┘
```

**Example Output (YAML):**

```yaml
ingress:
  name: web
  namespace: default
  class: nginx
  hosts:
    - example.com
  address: 34.56.78.1
  rules:
    - host: example.com
      paths:
        - path: /
          pathType: Prefix
          service: web-service
          servicePort: 80
  tls:
    - hosts:
        - example.com
      secretName: tls-cert
  age: 30d
```

**Notes:**

- Rules define path-based routing
- TLS configuration secures the connection
- Service port must match backing service

---

### `ops k8s ingresses create`

Create a new ingress for routing HTTP/HTTPS traffic.

This command creates an ingress with host rules, path routing, and optional TLS configuration.

**Usage:**

```bash
ops k8s ingresses create my-ingress --class-name nginx \
  --rule '{"host":"example.com","paths":[{"path":"/","path_type":"Prefix","service_name":"web","service_port":80}]}'

ops k8s ingresses create api-ingress --class-name nginx \
  --rule '{"host":"api.example.com","paths":[{"path":"/","path_type":"Prefix","service_name":"api","service_port":8080}]}'
```

**Arguments:**

| Argument | Type   | Description                     |
| -------- | ------ | ------------------------------- |
| `name`   | string | Name for the ingress (required) |

**Options:**

| Option         | Short | Type        | Default        | Description                        |
| -------------- | ----- | ----------- | -------------- | ---------------------------------- |
| `--class-name` | -     | string      | -              | Ingress class (e.g., nginx)        |
| `--namespace`  | `-n`  | string      | config default | Target namespace                   |
| `--rule`       | -     | string list | -              | Ingress rules as JSON (repeatable) |
| `--tls`        | -     | string list | -              | TLS config as JSON (repeatable)    |
| `--label`      | `-l`  | string list | -              | Labels in key=value format         |
| `--output`     | `-o`  | string      | `table`        | Output format                      |

**Rule JSON Format:**

```json
{
  "host": "example.com",
  "paths": [
    {
      "path": "/",
      "path_type": "Prefix",
      "service_name": "web-service",
      "service_port": 80
    },
    {
      "path": "/api",
      "path_type": "Prefix",
      "service_name": "api-service",
      "service_port": 8080
    }
  ]
}
```

**TLS JSON Format:**

```json
{
  "hosts": ["example.com", "www.example.com"],
  "secret_name": "tls-secret"
}
```

**Ingress Creation Examples:**

```bash
# Simple HTTP routing
ops k8s ingresses create web --class-name nginx \
  --rule '{"host":"example.com","paths":[{"path":"/","path_type":"Prefix","service_name":"web","service_port":80}]}'

# Multiple paths
ops k8s ingresses create app --class-name nginx \
  --rule '{
    "host":"app.example.com",
    "paths":[
      {"path":"/","path_type":"Prefix","service_name":"web","service_port":80},
      {"path":"/api","path_type":"Prefix","service_name":"api","service_port":8080}
    ]
  }'

# With TLS
ops k8s ingresses create secure --class-name nginx \
  --rule '{"host":"secure.example.com","paths":[{"path":"/","path_type":"Prefix","service_name":"app","service_port":443}]}' \
  --tls '{"hosts":["secure.example.com"],"secret_name":"tls-cert"}'
```

**Path Type Options:**

| Type                   | Meaning                                                              |
| ---------------------- | -------------------------------------------------------------------- |
| Prefix                 | Match URL path prefix (e.g., `/api` matches `/api`, `/api/v1`, etc.) |
| Exact                  | Exact path match only                                                |
| ImplementationSpecific | Controller-specific matching                                         |

**Example Output:**

```text
Created Ingress: web

┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Property      ┃ Value       ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ Name          │ web         │
│ Ingress Class │ nginx       │
│ Hosts         │ example.com │
│ Rules         │ 1           │
│ TLS Enabled   │ Yes         │
└───────────────┴─────────────┘
```

**Notes:**

- Rules must be valid JSON strings
- Service referenced in rule must exist
- TLS secret must exist in the same namespace
- Ingress requires an ingress controller to function

---

### `ops k8s ingresses update`

Update an existing ingress.

This command updates the ingress class, rules, or TLS configuration.

**Usage:**

```bash
ops k8s ingresses update my-ingress --class-name nginx
ops k8s ingresses update web \
  --rule '{"host":"www.example.com","paths":[{"path":"/","path_type":"Prefix","service_name":"web","service_port":80}]}'
ops k8s ingresses update api -n production --class-name nginx
```

**Arguments:**

| Argument | Type   | Description                    |
| -------- | ------ | ------------------------------ |
| `name`   | string | Name of the ingress (required) |

**Options:**

| Option         | Short | Type        | Default        | Description                    |
| -------------- | ----- | ----------- | -------------- | ------------------------------ |
| `--namespace`  | `-n`  | string      | config default | Namespace containing ingress   |
| `--class-name` | -     | string      | -              | New ingress class              |
| `--rule`       | -     | string list | -              | New rules as JSON (repeatable) |
| `--tls`        | -     | string list | -              | New TLS config as JSON         |
| `--output`     | `-o`  | string      | `table`        | Output format                  |

**Update Examples:**

```bash
# Update ingress class
ops k8s ingresses update web --class-name nginx

# Update routing rules
ops k8s ingresses update api \
  --rule '{"host":"api.example.com","paths":[{"path":"/","path_type":"Prefix","service_name":"api-v2","service_port":8080}]}'

# Update in specific namespace
ops k8s ingresses update internal -n backend --class-name internal
```

**Example Output:**

```text
Updated Ingress: web

┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Property      ┃ Value       ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ Name          │ web         │
│ Ingress Class │ nginx       │
│ Hosts         │ example.com │
│ Rules         │ 1           │
└───────────────┴─────────────┘
```

**Notes:**

- Rules changes take effect immediately
- Traffic is routed according to new configuration
- Existing connections may be interrupted

---

### `ops k8s ingresses delete`

Delete an ingress.

This command removes the ingress, making the service inaccessible via HTTP/HTTPS.

**Usage:**

```bash
ops k8s ingresses delete my-ingress
ops k8s ingresses delete web -n production
ops k8s ingresses delete api --force
```

**Arguments:**

| Argument | Type   | Description                              |
| -------- | ------ | ---------------------------------------- |
| `name`   | string | Name of the ingress to delete (required) |

**Options:**

| Option        | Short | Type    | Default        | Description                  |
| ------------- | ----- | ------- | -------------- | ---------------------------- |
| `--namespace` | `-n`  | string  | config default | Namespace containing ingress |
| `--force`     | `-f`  | boolean | false          | Skip confirmation            |

**Example Output:**

```text
Are you sure you want to delete ingress 'web' in namespace 'default'? [y/N]: y
Ingress 'web' deleted
```

**Notes:**

- Service is not deleted, only the ingress route
- External load balancer may take time to deprovision
- DNS should be updated to prevent traffic to deleted ingress

---

## Network Policy Commands

Network Policies define rules for pod-to-pod communication, implementing microsegmentation and security controls.

### `ops k8s network-policies list`

List all network policies in a namespace.

This command displays network policies with their rule counts and selector information.

**Usage:**

```bash
ops k8s network-policies list
ops k8s network-policies list -n production
ops k8s network-policies list --all-namespaces
ops k8s network-policies list -A
ops k8s network-policies list --output json
```

**Options:**

| Option             | Short | Type    | Default        | Description                |
| ------------------ | ----- | ------- | -------------- | -------------------------- |
| `--namespace`      | `-n`  | string  | config default | Target namespace           |
| `--all-namespaces` | `-A`  | boolean | false          | List across all namespaces |
| `--selector`       | `-l`  | string  | -              | Label selector to filter   |
| `--output`         | `-o`  | string  | `table`        | Output format              |

**Example Output (Table):**

```text
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━┓
┃ Name            ┃ Namespace ┃ Policy Types   ┃ Ingress Rules ┃ Egress Rules ┃ Age ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━┩
│ default-deny    │ default   │ Ingress        │ 0             │ -            │ 60d │
│ allow-web       │ default   │ Ingress        │ 1             │ -            │ 45d │
│ frontend-egress │ default   │ Egress         │ -             │ 2            │ 30d │
│ db-allow        │ default   │ Ingress,Egress │ 1             │ 1            │ 15d │
└─────────────────┴───────────┴────────────────┴───────────────┴──────────────┴─────┘
```

**Policy Type:**

| Type    | Purpose                             |
| ------- | ----------------------------------- |
| Ingress | Controls incoming traffic to pods   |
| Egress  | Controls outgoing traffic from pods |
| Both    | Controls both directions            |

**Notes:**

- Policies apply to pods matching selector labels
- Default deny policies block all traffic unless explicitly allowed
- Requires network plugin that supports network policies

---

### `ops k8s network-policies get`

Get detailed information about a network policy.

This command displays the complete network policy configuration including rules and selectors.

**Usage:**

```bash
ops k8s network-policies get my-policy
ops k8s network-policies get allow-web -n production
ops k8s network-policies get default-deny --output json
ops k8s network-policies get db-policy -o yaml
```

**Arguments:**

| Argument | Type   | Description                           |
| -------- | ------ | ------------------------------------- |
| `name`   | string | Name of the network policy (required) |

**Options:**

| Option        | Short | Type   | Default        | Description                 |
| ------------- | ----- | ------ | -------------- | --------------------------- |
| `--namespace` | `-n`  | string | config default | Namespace containing policy |
| `--output`    | `-o`  | string | `table`        | Output format               |

**Example Output (Table):**

```text
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Property      ┃ Value     ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ Name          │ allow-web │
│ Namespace     │ default   │
│ Pod Selector  │ app: web  │
│ Policy Types  │ Ingress   │
│ Ingress Rules │ 1         │
│ Egress Rules  │ -         │
│ Age           │ 45d       │
└───────────────┴───────────┘
```

**Example Output (YAML):**

```yaml
networkPolicy:
  name: allow-web
  namespace: default
  podSelector:
    matchLabels:
      app: web
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              tier: frontend
      ports:
        - protocol: TCP
          port: 80
  age: 45d
```

**Notes:**

- Pod selector defines which pods the policy applies to
- Rules show allowed sources/destinations
- Empty from/to list means allow all

---

### `ops k8s network-policies create`

Create a new network policy to control traffic flow.

This command creates a network policy with selector labels and policy types.

**Usage:**

```bash
ops k8s network-policies create deny-all --pod-selector app=web --policy-type Ingress
ops k8s network-policies create allow-web --pod-selector tier=backend --policy-type Ingress --policy-type Egress
ops k8s network-policies create db-access -l env=production --pod-selector app=postgres
```

**Arguments:**

| Argument | Type   | Description                            |
| -------- | ------ | -------------------------------------- |
| `name`   | string | Name for the network policy (required) |

**Options:**

| Option           | Short | Type        | Default        | Description                                   |
| ---------------- | ----- | ----------- | -------------- | --------------------------------------------- |
| `--namespace`    | `-n`  | string      | config default | Target namespace                              |
| `--pod-selector` | -     | string list | -              | Pod selector in key=value format (repeatable) |
| `--policy-type`  | -     | string list | -              | Policy type: Ingress or Egress (repeatable)   |
| `--label`        | `-l`  | string list | -              | Labels in key=value format (repeatable)       |
| `--output`       | `-o`  | string      | `table`        | Output format                                 |

**Pod Selector Matching:**

```bash
# Match pods with specific label
ops k8s network-policies create policy1 --pod-selector app=web

# Match pods with multiple labels
ops k8s network-policies create policy2 --pod-selector app=backend --pod-selector tier=api

# Match all pods in namespace (empty selector)
ops k8s network-policies create deny-all-ingress
```

**Network Policy Creation Examples:**

```bash
# Default deny all ingress
ops k8s network-policies create default-deny \
  --policy-type Ingress

# Allow traffic to web pods
ops k8s network-policies create allow-web \
  --pod-selector app=web \
  --policy-type Ingress

# Allow egress for API pods
ops k8s network-policies create api-egress \
  --pod-selector app=api \
  --policy-type Egress

# Bidirectional policy for database
ops k8s network-policies create db-access \
  --pod-selector app=postgres \
  --policy-type Ingress \
  --policy-type Egress \
  -l env=production
```

**Example Output:**

```text
Created NetworkPolicy: allow-web

┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Property      ┃ Value     ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ Name          │ allow-web │
│ Pod Selector  │ app: web  │
│ Policy Types  │ Ingress   │
│ Ingress Rules │ 0         │
│ Egress Rules  │ -         │
└───────────────┴───────────┘
```

**Policy Type Considerations:**

| Type         | Effect                                                |
| ------------ | ----------------------------------------------------- |
| Ingress only | Pod can send traffic out, but only receive if allowed |
| Egress only  | Pod can receive traffic, but only send if allowed     |
| Both         | Both directions must be explicitly allowed            |
| Neither      | No policies applied (default allow)                   |

**Notes:**

- Empty rules mean deny all for that direction
- Policies are additive (multiple policies on same pod combine with OR)
- Requires network plugin (Calico, Cilium, etc.)
- Good practice: Start with default deny, then allow specific traffic

---

### `ops k8s network-policies delete`

Delete a network policy.

This command removes a network policy, allowing traffic that was previously restricted.

**Usage:**

```bash
ops k8s network-policies delete my-policy
ops k8s network-policies delete deny-all -n production
ops k8s network-policies delete allow-web --force
```

**Arguments:**

| Argument | Type   | Description                             |
| -------- | ------ | --------------------------------------- |
| `name`   | string | Name of the policy to delete (required) |

**Options:**

| Option        | Short | Type    | Default        | Description                 |
| ------------- | ----- | ------- | -------------- | --------------------------- |
| `--namespace` | `-n`  | string  | config default | Namespace containing policy |
| `--force`     | `-f`  | boolean | false          | Skip confirmation           |

**Example Output:**

```text
Are you sure you want to delete network policy 'allow-web' in namespace 'default'? [y/N]: y
NetworkPolicy 'allow-web' deleted
```

**Warnings:**

- Deletion immediately affects traffic rules
- Pods may lose connectivity if no other policies allow traffic
- Test changes in non-production first

**Notes:**

- Deletion is immediate
- No automatic notification to pods
- Other policies continue to apply

---

## Troubleshooting

| Issue                                     | Cause                                        | Solution             |
| ----------------------------------------- | -------------------------------------------- | -------------------- |
| Service has no endpoints                  | Pod selector doesn't                         | Verify selector      |
| LoadBalancer stuck in pending             | Cloud provider integration                   | Check cloud provider |
| Ingress not receiving traffic             | Ingress controller not                       | Install ingress      |
| Ingress address keeps changing            | Load balancer keeps                          | Check DNS TTL and    |
| Network policy blocking traffic           | Rules too restrictive or missing allow rules | Review rules and     |
| Cannot reach service from outside cluster | Service type is ClusterIP instead of         | Change service type  |
| Services can't reach each other           | Network policies                             | Create ingress       |
| Ingress rules                             | Invalid JSON in rules                        | Verify JSON syntax   |
| Port mapping not working                  | Service port and pod                         | Verify pod listens   |

---

## See Also

- [Core Commands](./core.md) - Manage cluster, nodes, and namespaces
- [Workloads Commands](./workloads.md) - Manage pods, deployments, and other workload resources
- [Kubernetes Plugin Index](../index.md) - Complete Kubernetes plugin documentation
- [Examples](../examples.md) - Practical examples and use cases
- [TUI Overview](../tui.md) - Terminal UI for cluster exploration
