# Kubernetes Plugin > Ecosystem > External Secrets

[< Back to Index](../index.md) | [Commands](../commands/) | [Ecosystem](./) | [TUI](../tui.md) | [Examples](../examples.md)

---

## Table of Contents

- [Overview](#overview)
  - [What is External Secrets?](#what-is-external-secrets)
  - [Why Use External Secrets?](#why-use-external-secrets)
  - [Integration with K8s Plugin](#integration-with-k8s-plugin)
- [Prerequisites](#prerequisites)
  - [CRD Installation](#crd-installation)
  - [Operator Installation](#operator-installation)
  - [Version Requirements](#version-requirements)
- [Detection](#detection)
- [Configuration](#configuration)
  - [Plugin Configuration](#plugin-configuration)
  - [Namespace Configuration](#namespace-configuration)
- [Command Reference](#command-reference)
  - [Secret Stores](#secret-stores)
  - [Cluster Secret Stores](#cluster-secret-stores)
  - [External Secrets](#external-secrets)
  - [ESO Operator Status](#eso-operator-status)
- [Integration Examples](#integration-examples)
  - [Vault Integration](#vault-integration)
  - [AWS Secrets Manager Integration](#aws-secrets-manager-integration)
  - [Multi-Environment Setup](#multi-environment-setup)
- [Troubleshooting](#troubleshooting)
- [See Also](#see-also)

---

## Overview

### What is External Secrets?

External Secrets Operator (ESO) is a Kubernetes operator that enables secure management of secrets from external secret
management systems. It automatically synchronizes secrets from external backends (Vault, AWS Secrets Manager, Azure Key
Vault, Google Cloud Secret Manager, and more) into Kubernetes Secrets.

Key capabilities:

- **Multi-provider support** - Vault, AWS, Azure, GCP, HashiCorp Cloud Platform, and more
- **Automatic synchronization** - Keeps K8s secrets in sync with external backends
- **SecretStore abstraction** - Define where secrets come from and how to authenticate
- **Data templating** - Transform and template secrets as they're synchronized
- **Multi-tenancy** - Namespace-scoped (SecretStore) and cluster-scoped (ClusterSecretStore) stores
- **RBAC integration** - Control who can manage secrets and stores

### Why Use External Secrets?

1. **Single Source of Truth** - Manage all secrets in one centralized external system
2. **Security** - Reduces secrets stored in etcd, uses ephemeral credentials
3. **Compliance** - Audit trails in external systems, separation of concerns
4. **Automation** - Automatic rotation and synchronization of secrets
5. **Integration** - Works with existing secret management infrastructure

### Integration with K8s Plugin

These tools are CRD-based resources managed via Kubernetes CustomResourcesApi. The plugin provides convenient CLI
commands for:

- Listing and viewing SecretStores and ClusterSecretStores
- Creating and managing external secret definitions
- Monitoring synchronization status
- Checking ESO operator health

---

## Prerequisites

### CRD Installation

External Secrets requires Custom Resource Definitions (CRDs) for:

- `ExternalSecret` - Namespace-scoped secret definitions
- `SecretStore` - Namespace-scoped secret backend configurations
- `ClusterSecretStore` - Cluster-scoped secret backend configurations
- `PushSecret` - Namespace-scoped for pushing secrets to external backends

CRDs are installed when you deploy the External Secrets Operator.

### Operator Installation

Install the External Secrets Operator using Helm:

```bash
# Add the External Secrets Helm repository
helm repo add external-secrets https://charts.external-secrets.io

# Update Helm repositories
helm repo update

# Install External Secrets Operator in external-secrets namespace
helm install external-secrets \
  external-secrets/external-secrets \
  -n external-secrets \
  --create-namespace \
  --set installCRDs=true

# Verify installation
kubectl get pods -n external-secrets
```

### Version Requirements

| External Secrets Version | Kubernetes | Status        |
| ------------------------ | ---------- | ------------- |
| 0.8+                     | 1.25+      | Full support  |
| 0.7                      | 1.21+      | Maintenance   |
| < 0.7                    | Legacy     | Not supported |

---

## Detection

The plugin automatically detects External Secrets availability by:

1. **Checking for CRDs** - Looks for `externalsecret.external-secrets.io` CRD
2. **Verifying operator pods** - Checks if ESO controller pods are running in `external-secrets` namespace
3. **API accessibility** - Confirms API server can list ExternalSecret resources
4. **Provider availability** - Tests connection to configured secret stores

Detection occurs when you first run an ESO-related command. If External Secrets is not detected, you'll receive a clear
error message with installation instructions.

---

## Configuration

### Plugin Configuration

Add External Secrets configuration to your ops config file (`~/.config/ops/config.yaml`):

```yaml
plugins:
  kubernetes:
    # Enable External Secrets commands
    external_secrets:
      # Enable/disable the feature (default: true if ESO is installed)
      enabled: true
      # Default namespace for SecretStore lookups
      default_namespace: "default"
      # Timeout for sync operations (seconds)
      sync_timeout: 30
      # Number of retries for failed operations
      retries: 3
      # Supported providers (for validation and help)
      supported_providers:
        - vault
        - aws-secrets-manager
        - azure-key-vault
        - google-secret-manager
        - hcp-vault
        - delinea-vault
```

### Namespace Configuration

Configure which namespaces have SecretStores:

```bash
# Default behavior - use active namespace or 'default'
ops k8s secret-stores list

# Specify namespace
ops k8s secret-stores list -n production

# List across all namespaces
# Use label selectors to filter
ops k8s secret-stores list -l provider=vault -n production
```

---

## Command Reference

### Secret Stores

SecretStores are namespace-scoped resources that define how to authenticate to an external secret backend.

#### `ops k8s secret-stores list`

List SecretStores in a namespace.

```bash
ops k8s secret-stores list [OPTIONS]
```

**Arguments:** None

**Options:**

| Option        | Short | Type   | Default | Description                             |
| ------------- | ----- | ------ | ------- | --------------------------------------- |
| `--namespace` | `-n`  | string | default | Kubernetes namespace                    |
| `--selector`  | `-l`  | string | -       | Label selector (e.g., 'provider=vault') |
| `--output`    | `-o`  | string | table   | Output format: table, json, yaml        |

**Example:**

```bash
# List all SecretStores in default namespace
ops k8s secret-stores list

# List SecretStores in production namespace
ops k8s secret-stores list -n production

# List only Vault-based stores
ops k8s secret-stores list -l provider=vault

# Output as JSON
ops k8s secret-stores list -o json
```

**Example Output:**

```text
Secret Stores
Name                  Namespace    Provider        Ready  Message                    Age
vault-backend        default      vault           true   Secret store initialized   2d
aws-store            production   aws-secrets     true   Connected to AWS           5h
azure-kv-store       staging      azure-keyvault  false  Authentication failed      10m
```

#### `ops k8s secret-stores get`

Get details of a specific SecretStore.

```bash
ops k8s secret-stores get NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description             |
| -------- | -------- | ----------------------- |
| NAME     | yes      | Name of the SecretStore |

**Options:**

| Option        | Short | Type   | Default | Description                      |
| ------------- | ----- | ------ | ------- | -------------------------------- |
| `--namespace` | `-n`  | string | default | Kubernetes namespace             |
| `--output`    | `-o`  | string | table   | Output format: table, json, yaml |

**Example:**

```bash
# Get Vault store details
ops k8s secret-stores get vault-backend

# Get store in specific namespace
ops k8s secret-stores get aws-store -n production

# View full YAML definition
ops k8s secret-stores get vault-backend -o yaml
```

**Example Output (YAML):**

```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: vault-backend
  namespace: default
spec:
  provider:
    vault:
      server: "https://vault.example.com:8200"
      path: "secret"
      version: "v2"
      auth:
        kubernetes:
          mountPath: "kubernetes"
          role: "my-role"
status:
  conditions:
    - type: Ready
      status: "True"
      reason: "Valid"
      message: "Secret store initialized"
  lastCheckTime: "2024-02-16T10:30:45Z"
```

#### `ops k8s secret-stores create`

Create a new SecretStore.

```bash
ops k8s secret-stores create NAME --provider-config CONFIG [OPTIONS]
```

**Arguments:**

| Argument | Required | Description              |
| -------- | -------- | ------------------------ |
| NAME     | yes      | Name for the SecretStore |

**Options:**

| Option              | Short | Type   | Default  | Description                      |
| ------------------- | ----- | ------ | -------- | -------------------------------- |
| `--provider-config` | -     | string | required | Provider configuration as JSON   |
| `--namespace`       | `-n`  | string | default  | Kubernetes namespace             |
| `--label`           | `-l`  | string | -        | Labels (key=value, repeatable)   |
| `--output`          | `-o`  | string | table    | Output format: table, json, yaml |

**Example:**

```bash
# Create Vault SecretStore
ops k8s secret-stores create vault-backend \
  --provider-config '{"vault":{"server":"https://vault.example.com:8200","path":"secret","version":"v2","auth":{"kubernetes":{"mountPath":"kubernetes","role":"my-role"}}}}'

# Create with labels
ops k8s secret-stores create vault-prod \
  -n production \
  -l environment=prod \
  -l provider=vault \
  --provider-config '{"vault":{"server":"https://vault.prod.com:8200","path":"secret","version":"v2","auth":{"kubernetes":{"mountPath":"kubernetes","role":"prod-role"}}}}'

# AWS Secrets Manager store
ops k8s secret-stores create aws-backend \
  --provider-config '{"aws":{"service":"SecretsManager","region":"us-east-1","auth":{"jwt":{"serviceAccountRef":{"name":"external-secrets-sa"}}}}}'
```

**Provider Configuration Examples:**

Vault with Kubernetes auth:

```json
{
  "vault": {
    "server": "https://vault.example.com:8200",
    "path": "secret",
    "version": "v2",
    "auth": {
      "kubernetes": {
        "mountPath": "kubernetes",
        "role": "my-role",
        "serviceAccountRef": {
          "name": "external-secrets-sa"
        }
      }
    }
  }
}
```

AWS Secrets Manager:

```json
{
  "aws": {
    "service": "SecretsManager",
    "region": "us-east-1",
    "auth": {
      "jwt": {
        "serviceAccountRef": {
          "name": "external-secrets-sa"
        }
      }
    }
  }
}
```

Azure Key Vault:

```json
{
  "azurekv": {
    "authType": "workloadIdentity",
    "vaultUrl": "https://myvault.vault.azure.net",
    "tenantId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "clientId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
  }
}
```

#### `ops k8s secret-stores delete`

Delete a SecretStore.

```bash
ops k8s secret-stores delete NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                       |
| -------- | -------- | --------------------------------- |
| NAME     | yes      | Name of the SecretStore to delete |

**Options:**

| Option        | Short | Type   | Default | Description              |
| ------------- | ----- | ------ | ------- | ------------------------ |
| `--namespace` | `-n`  | string | default | Kubernetes namespace     |
| `--force`     | `-f`  | bool   | false   | Skip confirmation prompt |

**Example:**

```bash
# Delete with confirmation
ops k8s secret-stores delete vault-backend

# Delete without confirmation
ops k8s secret-stores delete vault-backend --force

# Delete from specific namespace
ops k8s secret-stores delete aws-store -n production --force
```

---

### Cluster Secret Stores

ClusterSecretStores are cluster-scoped resources that define secret backends accessible to any namespace.

#### `ops k8s cluster-secret-stores list`

List all ClusterSecretStores in the cluster.

```bash
ops k8s cluster-secret-stores list [OPTIONS]
```

**Arguments:** None

**Options:**

| Option       | Short | Type   | Default | Description                             |
| ------------ | ----- | ------ | ------- | --------------------------------------- |
| `--selector` | `-l`  | string | -       | Label selector (e.g., 'provider=vault') |
| `--output`   | `-o`  | string | table   | Output format: table, json, yaml        |

**Example:**

```bash
# List all ClusterSecretStores
ops k8s cluster-secret-stores list

# Filter by provider
ops k8s cluster-secret-stores list -l provider=aws

# Output as JSON
ops k8s cluster-secret-stores list -o json
```

**Example Output:**

```text
Cluster Secret Stores
Name              Provider        Ready  Message                      Age
vault-global      vault           true   Secret store initialized     7d
aws-global        aws-secrets     true   Connected to AWS             3d
azure-global      azure-keyvault  false  Invalid credentials          2h
```

#### `ops k8s cluster-secret-stores get`

Get details of a specific ClusterSecretStore.

```bash
ops k8s cluster-secret-stores get NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                    |
| -------- | -------- | ------------------------------ |
| NAME     | yes      | Name of the ClusterSecretStore |

**Options:**

| Option     | Short | Type   | Default | Description                      |
| ---------- | ----- | ------ | ------- | -------------------------------- |
| `--output` | `-o`  | string | table   | Output format: table, json, yaml |

**Example:**

```bash
# Get ClusterSecretStore details
ops k8s cluster-secret-stores get vault-global

# View as YAML
ops k8s cluster-secret-stores get vault-global -o yaml
```

#### `ops k8s cluster-secret-stores create`

Create a new ClusterSecretStore (cluster-scoped).

```bash
ops k8s cluster-secret-stores create NAME --provider-config CONFIG [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                     |
| -------- | -------- | ------------------------------- |
| NAME     | yes      | Name for the ClusterSecretStore |

**Options:**

| Option              | Short | Type   | Default  | Description                      |
| ------------------- | ----- | ------ | -------- | -------------------------------- |
| `--provider-config` | -     | string | required | Provider configuration as JSON   |
| `--label`           | `-l`  | string | -        | Labels (key=value, repeatable)   |
| `--output`          | `-o`  | string | table    | Output format: table, json, yaml |

**Example:**

```bash
# Create cluster-wide Vault store
ops k8s cluster-secret-stores create vault-global \
  --provider-config '{"vault":{"server":"https://vault.example.com:8200","path":"secret","version":"v2","auth":{"kubernetes":{"mountPath":"kubernetes","role":"global-role"}}}}'

# Create cluster-wide AWS store
ops k8s cluster-secret-stores create aws-global \
  -l environment=production \
  --provider-config '{"aws":{"service":"SecretsManager","region":"us-east-1"}}'
```

#### `ops k8s cluster-secret-stores delete`

Delete a ClusterSecretStore.

```bash
ops k8s cluster-secret-stores delete NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                              |
| -------- | -------- | ---------------------------------------- |
| NAME     | yes      | Name of the ClusterSecretStore to delete |

**Options:**

| Option    | Short | Type | Default | Description              |
| --------- | ----- | ---- | ------- | ------------------------ |
| `--force` | `-f`  | bool | false   | Skip confirmation prompt |

**Example:**

```bash
# Delete with confirmation
ops k8s cluster-secret-stores delete vault-global

# Delete without confirmation
ops k8s cluster-secret-stores delete aws-global --force
```

---

### External Secrets

ExternalSecrets define which secrets to synchronize from an external backend and create a corresponding Kubernetes
Secret.

#### `ops k8s external-secrets list`

List ExternalSecrets in a namespace.

```bash
ops k8s external-secrets list [OPTIONS]
```

**Arguments:** None

**Options:**

| Option        | Short | Type   | Default | Description                      |
| ------------- | ----- | ------ | ------- | -------------------------------- |
| `--namespace` | `-n`  | string | default | Kubernetes namespace             |
| `--selector`  | `-l`  | string | -       | Label selector                   |
| `--output`    | `-o`  | string | table   | Output format: table, json, yaml |

**Example:**

```bash
# List all ExternalSecrets
ops k8s external-secrets list

# List in production namespace
ops k8s external-secrets list -n production

# Filter by label
ops k8s external-secrets list -l app=myapp

# JSON output
ops k8s external-secrets list -o json
```

**Example Output:**

```text
External Secrets
Name          Namespace   Store         Store Kind      Refresh   Keys  Ready  Age
db-creds      default     vault-backend SecretStore     1h        3     true   5d
api-keys      production  aws-store     SecretStore     30m       5     true   2d
tls-certs     staging     vault-prod    ClusterSecretStore 2h      2     false  4h
```

#### `ops k8s external-secrets get`

Get details of an ExternalSecret.

```bash
ops k8s external-secrets get NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                |
| -------- | -------- | -------------------------- |
| NAME     | yes      | Name of the ExternalSecret |

**Options:**

| Option        | Short | Type   | Default | Description                      |
| ------------- | ----- | ------ | ------- | -------------------------------- |
| `--namespace` | `-n`  | string | default | Kubernetes namespace             |
| `--output`    | `-o`  | string | table   | Output format: table, json, yaml |

**Example:**

```bash
# Get ExternalSecret details
ops k8s external-secrets get db-creds

# Get from specific namespace
ops k8s external-secrets get db-creds -n production

# View full YAML
ops k8s external-secrets get db-creds -o yaml
```

**Example Output (YAML):**

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: db-creds
  namespace: default
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: db-credentials
    template:
      type: Opaque
      data:
        connection-string: "{{ .dbUrl }}"
        username: "{{ .dbUser }}"
        password: "{{ .dbPass }}"
  data:
    - secretKey: dbUrl
      remoteRef:
        key: secret/data/database
        property: url
    - secretKey: dbUser
      remoteRef:
        key: secret/data/database
        property: username
    - secretKey: dbPass
      remoteRef:
        key: secret/data/database
        property: password
status:
  conditions:
    - type: Ready
      status: "True"
      reason: "SecretSynced"
      message: "Secret synced successfully"
  lastSyncTime: "2024-02-16T10:30:45Z"
  syncedResourceVersion: "12345"
```

#### `ops k8s external-secrets create`

Create an ExternalSecret.

```bash
ops k8s external-secrets create NAME --store STORE [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                 |
| -------- | -------- | --------------------------- |
| NAME     | yes      | Name for the ExternalSecret |

**Options:**

| Option               | Short | Type   | Default     | Description                                   |
| -------------------- | ----- | ------ | ----------- | --------------------------------------------- |
| `--store`            | -     | string | required    | SecretStore or ClusterSecretStore name        |
| `--store-kind`       | -     | string | SecretStore | Store kind: SecretStore or ClusterSecretStore |
| `--namespace`        | `-n`  | string | default     | Kubernetes namespace                          |
| `--data`             | -     | string | -           | Data mapping as JSON (repeatable)             |
| `--target-name`      | -     | string | NAME        | Override target K8s Secret name               |
| `--refresh-interval` | -     | string | 1h          | Sync refresh interval (e.g., 1h, 30m, 15s)    |
| `--label`            | `-l`  | string | -           | Labels (key=value, repeatable)                |
| `--output`           | `-o`  | string | table       | Output format: table, json, yaml              |

**Example:**

```bash
# Create simple ExternalSecret
ops k8s external-secrets create db-creds \
  --store vault-backend \
  --data '{"secretKey":"password","remoteRef":{"key":"secret/data/myapp","property":"password"}}'

# Multiple data fields
ops k8s external-secrets create app-secrets \
  --store vault-backend \
  --data '{"secretKey":"db_password","remoteRef":{"key":"secret/data/db","property":"password"}}' \
  --data '{"secretKey":"api_key","remoteRef":{"key":"secret/data/api","property":"key"}}'

# AWS Secrets Manager with ClusterSecretStore
ops k8s external-secrets create aws-secrets \
  --store aws-global \
  --store-kind ClusterSecretStore \
  --refresh-interval 30m \
  --data '{"secretKey":"api_key","remoteRef":{"key":"myapp/api_key"}}'

# With custom target secret name and labels
ops k8s external-secrets create vault-tls \
  -n production \
  --store vault-prod \
  --target-name tls-certificate \
  --refresh-interval 2h \
  -l app=myapp \
  -l component=tls \
  --data '{"secretKey":"tls.crt","remoteRef":{"key":"secret/data/tls","property":"cert"}}' \
  --data '{"secretKey":"tls.key","remoteRef":{"key":"secret/data/tls","property":"key"}}'
```

**Data Field Mapping Format:**

Each `--data` argument is a JSON object with:

```json
{
  "secretKey": "key_in_kubernetes_secret",
  "remoteRef": {
    "key": "path_in_external_backend",
    "property": "optional_property_within_secret"
  }
}
```

For Vault:

```json
{
  "secretKey": "password",
  "remoteRef": {
    "key": "secret/data/myapp",
    "property": "password"
  }
}
```

For AWS Secrets Manager (no property needed):

```json
{
  "secretKey": "api_key",
  "remoteRef": {
    "key": "myapp/api_key"
  }
}
```

#### `ops k8s external-secrets delete`

Delete an ExternalSecret.

```bash
ops k8s external-secrets delete NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                          |
| -------- | -------- | ------------------------------------ |
| NAME     | yes      | Name of the ExternalSecret to delete |

**Options:**

| Option        | Short | Type   | Default | Description              |
| ------------- | ----- | ------ | ------- | ------------------------ |
| `--namespace` | `-n`  | string | default | Kubernetes namespace     |
| `--force`     | `-f`  | bool   | false   | Skip confirmation prompt |

**Example:**

```bash
# Delete with confirmation
ops k8s external-secrets delete db-creds

# Delete without confirmation
ops k8s external-secrets delete db-creds --force

# Delete from specific namespace
ops k8s external-secrets delete api-keys -n production --force
```

#### `ops k8s external-secrets sync-status`

Show synchronization status for an ExternalSecret.

```bash
ops k8s external-secrets sync-status NAME [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                |
| -------- | -------- | -------------------------- |
| NAME     | yes      | Name of the ExternalSecret |

**Options:**

| Option        | Short | Type   | Default | Description                      |
| ------------- | ----- | ------ | ------- | -------------------------------- |
| `--namespace` | `-n`  | string | default | Kubernetes namespace             |
| `--output`    | `-o`  | string | table   | Output format: table, json, yaml |

**Example:**

```bash
# Check sync status
ops k8s external-secrets sync-status db-creds

# Check in specific namespace
ops k8s external-secrets sync-status db-creds -n production

# JSON output for scripting
ops k8s external-secrets sync-status db-creds -o json
```

**Example Output:**

```text
Sync Status: db-creds
Status: Ready
Last Sync Time: 2024-02-16T10:30:45Z
Sync Generation: 12345
Conditions:
  Type: Ready
  Status: True
  Reason: SecretSynced
  Message: Secret synced successfully
  Last Transition: 2024-02-16T10:25:00Z
```

---

### ESO Operator Status

#### `ops k8s eso status`

Show External Secrets Operator health and status.

```bash
ops k8s eso status [OPTIONS]
```

**Arguments:** None

**Options:**

| Option     | Short | Type   | Default | Description                      |
| ---------- | ----- | ------ | ------- | -------------------------------- |
| `--output` | `-o`  | string | table   | Output format: table, json, yaml |

**Example:**

```bash
# Check ESO status
ops k8s eso status

# JSON output
ops k8s eso status -o json
```

**Example Output:**

```text
External Secrets Operator
Namespace: external-secrets
Status: Running
Pod Count: 2
Ready Replicas: 2

Pods:
Name                                          Ready  Status    Restarts  Age
external-secrets-5d6f8b6c9d-abc12            1/1    Running   0         7d
external-secrets-webhook-7c8d9e5f4g-def34    1/1    Running   0         7d

CRD Status:
- externalsecret.external-secrets.io: Installed
- secretstore.external-secrets.io: Installed
- clustersecretstore.external-secrets.io: Installed
```

---

## Integration Examples

### Vault Integration

This example shows a complete setup for synchronizing secrets from HashiCorp Vault.

**Prerequisites:**

- Vault instance running with KV v2 secrets engine at `secret/`
- Kubernetes auth method enabled in Vault
- Service account `external-secrets-sa` in the cluster

**Step 1: Create SecretStore**

```bash
ops k8s secret-stores create vault-backend \
  --provider-config '{"vault":{"server":"https://vault.example.com:8200","path":"secret","version":"v2","auth":{"kubernetes":{"mountPath":"kubernetes","role":"my-role","serviceAccountRef":{"name":"external-secrets-sa"}}}}}'
```

**Step 2: Create ExternalSecret**

```bash
# Database credentials
ops k8s external-secrets create db-credentials \
  --store vault-backend \
  --target-name database-secret \
  --refresh-interval 1h \
  -l app=myapp \
  --data '{"secretKey":"username","remoteRef":{"key":"secret/data/database","property":"username"}}' \
  --data '{"secretKey":"password","remoteRef":{"key":"secret/data/database","property":"password"}}'

# API keys
ops k8s external-secrets create api-keys \
  --store vault-backend \
  --refresh-interval 30m \
  -l component=api \
  --data '{"secretKey":"stripe_key","remoteRef":{"key":"secret/data/payments","property":"stripe_api_key"}}' \
  --data '{"secretKey":"sendgrid_key","remoteRef":{"key":"secret/data/emails","property":"sendgrid_api_key"}}'
```

**Step 3: Verify Synchronization**

```bash
# List ExternalSecrets
ops k8s external-secrets list

# Check sync status
ops k8s external-secrets sync-status db-credentials

# View the created Kubernetes Secret
kubectl get secret database-secret -o yaml

# Check secret content (base64 decoded)
kubectl get secret database-secret -o jsonpath='{.data.username}' | base64 -d
```

**Step 4: Use in Pods**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
    - name: app
      image: myapp:latest
      env:
        - name: DB_USER
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: username
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: password
```

### AWS Secrets Manager Integration

This example demonstrates synchronizing secrets from AWS Secrets Manager.

**Prerequisites:**

- AWS account with Secrets Manager
- IRSA (IAM Roles for Service Accounts) configured
- Service account with AWS permissions

**Step 1: Create ClusterSecretStore (available across namespaces)**

```bash
ops k8s cluster-secret-stores create aws-secrets-global \
  --provider-config '{"aws":{"service":"SecretsManager","region":"us-east-1","auth":{"jwt":{"serviceAccountRef":{"name":"external-secrets-sa"}}}}}'
```

**Step 2: Create ExternalSecrets in multiple namespaces**

```bash
# Production namespace
ops k8s external-secrets create prod-api-keys \
  -n production \
  --store aws-secrets-global \
  --store-kind ClusterSecretStore \
  --refresh-interval 24h \
  --data '{"secretKey":"api_key","remoteRef":{"key":"prod/api_key"}}'

# Staging namespace
ops k8s external-secrets create staging-api-keys \
  -n staging \
  --store aws-secrets-global \
  --store-kind ClusterSecretStore \
  --refresh-interval 12h \
  --data '{"secretKey":"api_key","remoteRef":{"key":"staging/api_key"}}'
```

**Step 3: Verify Status**

```bash
# Check status in production
ops k8s external-secrets sync-status prod-api-keys -n production

# Check status in staging
ops k8s external-secrets sync-status staging-api-keys -n staging
```

### Multi-Environment Setup

This example shows managing secrets across dev, staging, and production environments.

**Step 1: Create environment-specific SecretStores**

```bash
# Development (local Vault)
ops k8s secret-stores create vault-dev \
  -n development \
  -l environment=dev \
  --provider-config '{"vault":{"server":"https://vault-dev.local:8200","path":"secret","version":"v2","auth":{"kubernetes":{"mountPath":"kubernetes","role":"dev-role"}}}}'

# Staging (staging Vault)
ops k8s secret-stores create vault-staging \
  -n staging \
  -l environment=staging \
  --provider-config '{"vault":{"server":"https://vault-staging.internal:8200","path":"secret","version":"v2","auth":{"kubernetes":{"mountPath":"kubernetes","role":"staging-role"}}}}'

# Production (highly secure Vault)
ops k8s secret-stores create vault-production \
  -n production \
  -l environment=production \
  --provider-config '{"vault":{"server":"https://vault.prod.example.com:8200","path":"secret","version":"v2","auth":{"kubernetes":{"mountPath":"kubernetes","role":"prod-role"}}}}'
```

**Step 2: Create same ExternalSecrets in each namespace**

```bash
for env in development staging production; do
  store="vault-${env}"
  ops k8s external-secrets create app-database \
    -n "$env" \
    --store "$store" \
    --refresh-interval 1h \
    -l environment="$env" \
    --data '{"secretKey":"host","remoteRef":{"key":"secret/data/$env/database","property":"host"}}' \
    --data '{"secretKey":"username","remoteRef":{"key":"secret/data/$env/database","property":"username"}}' \
    --data '{"secretKey":"password","remoteRef":{"key":"secret/data/$env/database","property":"password"}}'
done
```

**Step 3: Monitor all environments**

```bash
# List in all namespaces
for ns in development staging production; do
  echo "=== $ns ==="
  ops k8s external-secrets list -n "$ns"
done

# Check sync status across environments
for ns in development staging production; do
  echo "=== $ns ==="
  ops k8s external-secrets sync-status app-database -n "$ns"
done
```

---

## Troubleshooting

| Issue                          | Symptoms                               | Solution                                   |
| ------------------------------ | -------------------------------------- | ------------------------------------------ |
| **ESO not detected**           | "External Secrets Operator not found"  | Install ESO with Helm                      |
| **SecretStore not ready**      | `Ready: false`, auth failed            | Check auth credentials and provider config |
| **ExternalSecret not syncing** | Status "Not Ready", no error           | Check SecretStore is ready first           |
| **Secret not appearing**       | ExternalSecret ready but no K8s Secret | Check target secret name and namespace     |
| **Permission denied errors**   | ESO logs show "forbidden"              | Verify service account permissions         |
| **Timeouts during sync**       | Operations hang or timeout             | Increase `refreshInterval` setting         |
| **Stale secrets**              | Secrets not updating                   | Decrease `refreshInterval` for faster sync |
| **Multiple stores conflict**   | Unclear which store to use             | Use explicit `--store` parameter           |
| **JSON parsing errors**        | "Invalid JSON provider config"         | Validate JSON with a linter                |
| **CRD not found**              | "ExternalSecret not found"             | Ensure CRDs are installed in cluster       |

---

## See Also

- **[External Secrets Operator Documentation](https://external-secrets.io/)** - Official ESO docs
- **[Vault Integration Guide](https://external-secrets.io/latest/provider/vault/)** - Vault provider setup
- **[AWS Secrets Manager Integration](https://external-secrets.io/latest/provider/aws-secrets-manager/)** - AWS provider
  setup
- **[Kubernetes Secret Management](../index.md#configmaps-and-secrets)** - K8s secrets overview
- **[RBAC Commands](../commands/rbac.md)** - Managing service accounts and permissions
- **[Kubernetes Secrets Best Practices](https://kubernetes.io/docs/concepts/configuration/secret/)** - Official K8s
  secret docs
- **[Flux Integration](./flux.md)** - GitOps with synchronized secrets
- **[Cert-Manager Integration](./cert-manager.md)** - Certificate rotation with ESO
