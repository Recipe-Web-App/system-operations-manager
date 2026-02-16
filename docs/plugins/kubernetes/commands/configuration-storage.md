# Kubernetes Plugin > Commands > Configuration & Storage

[< Back to Index](../index.md) | [Commands](./) | [Ecosystem](../ecosystem/) | [TUI](../tui.md) | [Examples](../examples.md)

---

## Table of Contents

- [Overview](#overview)
- [Common Options](#common-options)
- [ConfigMaps](#configmaps)
  - [List ConfigMaps](#list-configmaps)
  - [Get ConfigMap](#get-configmap)
  - [Get ConfigMap Data](#get-configmap-data)
  - [Create ConfigMap](#create-configmap)
  - [Update ConfigMap](#update-configmap)
  - [Delete ConfigMap](#delete-configmap)
- [Secrets](#secrets)
  - [List Secrets](#list-secrets)
  - [Get Secret](#get-secret)
  - [Create Secret](#create-secret)
  - [Create TLS Secret](#create-tls-secret)
  - [Create Docker Registry Secret](#create-docker-registry-secret)
  - [Delete Secret](#delete-secret)
- [Persistent Volumes](#persistent-volumes)
  - [List Persistent Volumes](#list-persistent-volumes)
  - [Get Persistent Volume](#get-persistent-volume)
  - [Delete Persistent Volume](#delete-persistent-volume)
- [Persistent Volume Claims](#persistent-volume-claims)
  - [List Persistent Volume Claims](#list-persistent-volume-claims)
  - [Get Persistent Volume Claim](#get-persistent-volume-claim)
  - [Create Persistent Volume Claim](#create-persistent-volume-claim)
  - [Delete Persistent Volume Claim](#delete-persistent-volume-claim)
- [Storage Classes](#storage-classes)
  - [List Storage Classes](#list-storage-classes)
  - [Get Storage Class](#get-storage-class)
- [Troubleshooting](#troubleshooting)
- [See Also](#see-also)

---

## Overview

The configuration and storage commands manage Kubernetes resources related to application configuration and persistent
storage. These commands organize into five resource categories:

- **ConfigMaps** - Store non-sensitive configuration data as key-value pairs
- **Secrets** - Store sensitive data like passwords, API keys, and certificates
- **Persistent Volumes** - Cluster-scoped storage resources
- **Persistent Volume Claims** - Namespace-scoped requests for storage
- **Storage Classes** - Define storage provisioning policies

All commands support multiple output formats (table, JSON, YAML) and comprehensive filtering options.

---

## Common Options

Options available across most configuration and storage commands:

| Option             | Short | Type   | Default             | Description                                  |
| ------------------ | ----- | ------ | ------------------- | -------------------------------------------- |
| `--namespace`      | `-n`  | string | config or 'default' | Kubernetes namespace to operate in           |
| `--all-namespaces` | `-A`  | flag   | false               | List resources across all namespaces         |
| `--selector`       | `-l`  | string | none                | Filter by label selector (e.g., 'app=nginx') |
| `--output`         | `-o`  | string | table               | Output format: table, json, or yaml          |
| `--force`          | `-f`  | flag   | false               | Skip confirmation prompts                    |
| `--label`          | `-l`  | string | none                | Add labels to created resources (repeatable) |

---

## ConfigMaps

ConfigMaps store configuration data in key-value format. They are commonly used for application properties,
configuration files, and environment variables.

### List ConfigMaps

List all ConfigMaps in a namespace or across all namespaces.

```bash
ops k8s configmaps list
ops k8s configmaps list -n production
ops k8s configmaps list -A
ops k8s configmaps list -A -o json
ops k8s configmaps list -l app=web-server
```

**Options:**

| Option             | Short | Type   | Default             | Description                      |
| ------------------ | ----- | ------ | ------------------- | -------------------------------- |
| `--namespace`      | `-n`  | string | config or 'default' | Kubernetes namespace             |
| `--all-namespaces` | `-A`  | flag   | false               | List across all namespaces       |
| `--selector`       | `-l`  | string | none                | Filter by labels                 |
| `--output`         | `-o`  | string | table               | Output format: table, json, yaml |

**Example Output:**

```text
ConfigMaps
┌────────────────┬────────────┬──────┬─────┐
│ Name           │ Namespace  │ Keys │ Age │
├────────────────┼────────────┼──────┼─────┤
│ app-config     │ default    │ 3    │ 10d │
│ nginx-config   │ default    │ 2    │ 5d  │
│ db-connection  │ production │ 4    │ 2d  │
│ logging-config │ production │ 1    │ 1h  │
└────────────────┴────────────┴──────┴─────┘
```

**Notes:**

- Use `--all-namespaces` to monitor ConfigMaps across the entire cluster
- Filter by labels to find ConfigMaps matching specific criteria
- Use JSON or YAML output for programmatic processing

---

### Get ConfigMap

Retrieve detailed information about a specific ConfigMap, including all metadata and keys.

```bash
ops k8s configmaps get my-config
ops k8s configmaps get my-config -n production
ops k8s configmaps get my-config -o yaml
```

**Options:**

| Option        | Short | Type   | Default             | Description                      |
| ------------- | ----- | ------ | ------------------- | -------------------------------- |
| `--namespace` | `-n`  | string | config or 'default' | Kubernetes namespace             |
| `--output`    | `-o`  | string | table               | Output format: table, json, yaml |

**Example Output:**

```text
ConfigMap: app-config
┌───────────┬───────────────────────────┐
│ Field     │ Value                     │
├───────────┼───────────────────────────┤
│ Name      │ app-config                │
│ Namespace │ default                   │
│ Data Keys │ 3                         │
│ Age       │ 10 days                   │
│ Created   │ 2024-02-06T15:30:00Z      │
│ Labels    │ app=web, environment=prod │
└───────────┴───────────────────────────┘
```

**Notes:**

- Returns full resource metadata including labels and annotations
- Use `-o json` or `-o yaml` to see raw Kubernetes manifest
- Does not display the actual configuration values (use `get-data` for that)

---

### Get ConfigMap Data

Retrieve only the key-value data from a ConfigMap, useful for viewing actual configuration values.

```bash
ops k8s configmaps get-data my-config
ops k8s configmaps get-data my-config -n production
ops k8s configmaps get-data my-config -o json
```

**Options:**

| Option        | Short | Type   | Default             | Description                      |
| ------------- | ----- | ------ | ------------------- | -------------------------------- |
| `--namespace` | `-n`  | string | config or 'default' | Kubernetes namespace             |
| `--output`    | `-o`  | string | table               | Output format: table, json, yaml |

**Example Output:**

```text
ConfigMap Data: app-config
┌───────────────┬────────────────┐
│ Key           │ Value          │
├───────────────┼────────────────┤
│ database.host │ db.example.com │
│ database.port │ 5432           │
│ app.log_level │ INFO           │
└───────────────┴────────────────┘
```

**Notes:**

- Shows actual configuration data, unlike `get` which shows metadata
- Useful for debugging application configuration issues
- JSON output provides structured data for automation

---

### Create ConfigMap

Create a new ConfigMap with initial key-value data and optional labels.

```bash
ops k8s configmaps create my-config --data key1=value1 --data key2=value2
ops k8s configmaps create app-config -n production --data db.host=db.prod.com --data db.port=5432
ops k8s configmaps create my-config --label app=web --label env=prod
```

**Options:**

| Option        | Short | Type   | Default             | Description                        |
| ------------- | ----- | ------ | ------------------- | ---------------------------------- |
| `--namespace` | `-n`  | string | config or 'default' | Kubernetes namespace               |
| `--data`      | `-d`  | string | none                | Data entry (key=value, repeatable) |
| `--label`     | `-l`  | string | none                | Label (key=value, repeatable)      |
| `--output`    | `-o`  | string | table               | Output format: table, json, yaml   |

**Examples:**

Create basic ConfigMap:

```bash
ops k8s configmaps create logging-config \
  --data log.level=DEBUG \
  --data log.format=json
```

Create with labels:

```bash
ops k8s configmaps create app-settings \
  --data setting1=value1 \
  --data setting2=value2 \
  --label app=myapp \
  --label version=1.0 \
  --label env=production
```

Create in specific namespace:

```bash
ops k8s configmaps create db-config \
  -n production \
  --data host=db.example.com \
  --data port=5432 \
  --data pool_size=20
```

**Example Output:**

```text
Created ConfigMap: my-config
┌───────────┬───────────────────┐
│ Field     │ Value             │
├───────────┼───────────────────┤
│ Name      │ my-config         │
│ Namespace │ default           │
│ Status    │ Created           │
│ Data Keys │ 2                 │
│ Labels    │ app=web, env=prod │
└───────────┴───────────────────┘
```

**Notes:**

- Data values must be strings; use JSON format for complex structures in values
- Labels are metadata for filtering and organization
- Provide multiple `--data` options for multiple key-value pairs
- ConfigMaps are limited to 1MB in size

---

### Update ConfigMap

Update the data in an existing ConfigMap.

```bash
ops k8s configmaps update my-config --data key1=newvalue
ops k8s configmaps update my-config -n production --data db.port=5433
```

**Options:**

| Option        | Short | Type   | Default             | Description                        |
| ------------- | ----- | ------ | ------------------- | ---------------------------------- |
| `--namespace` | `-n`  | string | config or 'default' | Kubernetes namespace               |
| `--data`      | `-d`  | string | none                | Data entry (key=value, repeatable) |
| `--output`    | `-o`  | string | table               | Output format: table, json, yaml   |

**Examples:**

Update single key:

```bash
ops k8s configmaps update app-config --data log.level=WARNING
```

Update multiple keys:

```bash
ops k8s configmaps update app-config \
  --data db.host=newhost.example.com \
  --data db.port=5433 \
  --data cache.ttl=3600
```

**Example Output:**

```text
Updated ConfigMap: my-config
┌───────────┬──────────────────────┐
│ Field     │ Value                │
├───────────┼──────────────────────┤
│ Name      │ my-config            │
│ Namespace │ default              │
│ Status    │ Updated              │
│ Data Keys │ 3                    │
│ Modified  │ 2024-02-16T10:45:00Z │
└───────────┴──────────────────────┘
```

**Notes:**

- Only specified keys are updated; other keys remain unchanged
- Update triggers pod restarts if pods mount this ConfigMap
- Consider using versioned ConfigMaps for zero-downtime updates

---

### Delete ConfigMap

Delete a ConfigMap from the cluster.

```bash
ops k8s configmaps delete my-config
ops k8s configmaps delete my-config -n production
ops k8s configmaps delete my-config -f
```

**Options:**

| Option        | Short | Type   | Default             | Description              |
| ------------- | ----- | ------ | ------------------- | ------------------------ |
| `--namespace` | `-n`  | string | config or 'default' | Kubernetes namespace     |
| `--force`     | `-f`  | flag   | false               | Skip confirmation prompt |

**Example Output:**

```text
Are you sure you want to delete configmap 'my-config' in namespace 'default'? [y/N]: y
ConfigMap 'my-config' deleted
```

**Notes:**

- Requires confirmation unless `--force` is used
- Deletion may affect running pods that depend on this ConfigMap
- No recovery possible after deletion; consider backups if needed

---

## Secrets

Secrets store sensitive data like passwords, API keys, tokens, and certificates. Unlike ConfigMaps, Secrets have special
handling for sensitive information.

### List Secrets

List all Secrets in a namespace or across all namespaces.

```bash
ops k8s secrets list
ops k8s secrets list -n production
ops k8s secrets list -A
ops k8s secrets list -l app=api-server
```

**Options:**

| Option             | Short | Type   | Default             | Description                      |
| ------------------ | ----- | ------ | ------------------- | -------------------------------- |
| `--namespace`      | `-n`  | string | config or 'default' | Kubernetes namespace             |
| `--all-namespaces` | `-A`  | flag   | false               | List across all namespaces       |
| `--selector`       | `-l`  | string | none                | Filter by labels                 |
| `--output`         | `-o`  | string | table               | Output format: table, json, yaml |

**Example Output:**

```text
Secrets
┌────────────────┬────────────┬───────────────────┬──────┬─────┐
│ Name           │ Namespace  │ Type              │ Keys │ Age │
├────────────────┼────────────┼───────────────────┼──────┼─────┤
│ db-credentials │ default    │ Opaque            │ 2    │ 7d  │
│ api-key        │ default    │ Opaque            │ 1    │ 3d  │
│ tls-cert       │ default    │ kubernetes.io/tls │ 2    │ 30d │
│ registry-auth  │ production │ kubernetes.io/    │ 1    │ 5d  │
│                │            │ dockercfg         │      │     │
└────────────────┴────────────┴───────────────────┴──────┴─────┘
```

**Notes:**

- Secret values are base64-encoded, not shown in list output
- Use `--all-namespaces` to audit Secrets across the cluster
- Filter by labels to find Secrets for specific applications

---

### Get Secret

Retrieve details about a specific Secret. Values are hidden by default for security.

```bash
ops k8s secrets get my-secret
ops k8s secrets get my-secret -n production
ops k8s secrets get my-secret -o yaml
```

**Options:**

| Option        | Short | Type   | Default             | Description                      |
| ------------- | ----- | ------ | ------------------- | -------------------------------- |
| `--namespace` | `-n`  | string | config or 'default' | Kubernetes namespace             |
| `--output`    | `-o`  | string | table               | Output format: table, json, yaml |

**Example Output:**

```text
Secret: db-credentials
┌─────────────────┬────────────────────────────┐
│ Field           │ Value                      │
├─────────────────┼────────────────────────────┤
│ Name            │ db-credentials             │
│ Namespace       │ default                    │
│ Type            │ Opaque                     │
│ Data Keys       │ 2                          │
│ Age             │ 7 days                     │
│ Created         │ 2024-02-09T10:30:00Z       │
│ Labels          │ app=database, tier=backend │
│ Data (Redacted) │ [REDACTED]                 │
└─────────────────┴────────────────────────────┘
```

**Notes:**

- Secret values are hidden for security by default
- Use `-o json` or `-o yaml` to see the full manifest with base64-encoded values
- Be cautious when sharing Secret output; consider decoding values only in secure environments

---

### Create Secret

Create a new Secret with sensitive data.

```bash
ops k8s secrets create my-secret --data username=admin --data password=s3cret
ops k8s secrets create api-token --type Opaque --data token=<your-token>
ops k8s secrets create my-secret --label app=web --label env=prod
```

**Options:**

| Option        | Short | Type   | Default             | Description                            |
| ------------- | ----- | ------ | ------------------- | -------------------------------------- |
| `--namespace` | `-n`  | string | config or 'default' | Kubernetes namespace                   |
| `--data`      | `-d`  | string | none                | Data entry (key=value, repeatable)     |
| `--type`      | `-t`  | string | Opaque              | Secret type (Opaque, basic-auth, etc.) |
| `--label`     | `-l`  | string | none                | Label (key=value, repeatable)          |
| `--output`    | `-o`  | string | table               | Output format: table, json, yaml       |

**Examples:**

Create basic Opaque Secret:

```bash
ops k8s secrets create db-credentials \
  --data username=dbuser \
  --data password=securepassword123 \
  --data connection_string=postgres://dbuser:securepassword123@db.example.com:5432/mydb
```

Create Secret with labels:

```bash
ops k8s secrets create api-key \
  --type Opaque \
  --data key=<your-api-key> \
  --data secret=<your-api-secret> \
  --label app=payment-service \
  --label env=production
```

Create in specific namespace:

```bash
ops k8s secrets create prod-secrets \
  -n production \
  --data api_key=secret_key_123 \
  --data api_secret=secret_456
```

**Example Output:**

```text
Created Secret: my-secret
┌───────────┬───────────────────┐
│ Field     │ Value             │
├───────────┼───────────────────┤
│ Name      │ my-secret         │
│ Namespace │ default           │
│ Type      │ Opaque            │
│ Status    │ Created           │
│ Data Keys │ 2                 │
│ Labels    │ app=web, env=prod │
└───────────┴───────────────────┘
```

**Notes:**

- Secrets are base64-encoded in Kubernetes, but not encrypted by default
- Use proper encryption at rest for production clusters
- Limit access using RBAC to minimize exposure risk
- Data values can contain newlines and special characters

---

### Create TLS Secret

Create a Secret from TLS certificate and private key files.

```bash
ops k8s secrets create-tls my-tls --cert ./tls.crt --key ./tls.key
ops k8s secrets create-tls ingress-cert -n production --cert ./server.crt --key ./server.key
```

**Options:**

| Option        | Short | Type   | Default             | Description                          |
| ------------- | ----- | ------ | ------------------- | ------------------------------------ |
| `--namespace` | `-n`  | string | config or 'default' | Kubernetes namespace                 |
| `--cert`      |       | path   | required            | Path to PEM-encoded certificate file |
| `--key`       |       | path   | required            | Path to PEM-encoded private key file |
| `--label`     | `-l`  | string | none                | Label (key=value, repeatable)        |
| `--output`    | `-o`  | string | table               | Output format: table, json, yaml     |

**Examples:**

Create TLS Secret from certificate files:

```bash
ops k8s secrets create-tls https-cert \
  --cert /path/to/server.crt \
  --key /path/to/server.key
```

Create with labels for organization:

```bash
ops k8s secrets create-tls website-tls \
  --cert ./website.crt \
  --key ./website.key \
  --label app=website \
  --label renewal_date=2025-06-01 \
  --label provider=letsencrypt
```

Create in specific namespace:

```bash
ops k8s secrets create-tls api-tls \
  -n production \
  --cert /certs/api.crt \
  --key /certs/api.key
```

**Example Output:**

```text
Created TLS Secret: my-tls
┌───────────┬──────────────────────┐
│ Field     │ Value                │
├───────────┼──────────────────────┤
│ Name      │ my-tls               │
│ Namespace │ default              │
│ Type      │ kubernetes.io/tls    │
│ Status    │ Created              │
│ Keys      │ 2 (tls.crt, tls.key) │
│ Created   │ 2024-02-16T10:45:00Z │
└───────────┴──────────────────────┘
```

**Notes:**

- Certificate and key files must be in PEM format
- Both certificate and key files are required
- Use for HTTPS Ingress resources and pod-to-pod TLS
- TLS Secrets are stored with type `kubernetes.io/tls`

---

### Create Docker Registry Secret

Create a Secret for authenticating with Docker registries.

```bash
ops k8s secrets create-docker-registry my-reg \
  --server https://index.docker.io/v1/ \
  --username user \
  --password pass
```

**Options:**

| Option        | Short | Type   | Default             | Description                      |
| ------------- | ----- | ------ | ------------------- | -------------------------------- |
| `--namespace` | `-n`  | string | config or 'default' | Kubernetes namespace             |
| `--server`    |       | string | required            | Docker registry server URL       |
| `--username`  |       | string | required            | Registry username                |
| `--password`  |       | string | required            | Registry password                |
| `--email`     |       | string | empty               | Registry email address           |
| `--label`     | `-l`  | string | none                | Label (key=value, repeatable)    |
| `--output`    | `-o`  | string | table               | Output format: table, json, yaml |

**Examples:**

Create for Docker Hub:

```bash
ops k8s secrets create-docker-registry dockerhub \
  --server https://index.docker.io/v1/ \
  --username myusername \
  --password mytoken
```

Create for private registry:

```bash
ops k8s secrets create-docker-registry private-reg \
  --server registry.example.com \
  --username registry_user \
  --password registry_password \
  --email admin@example.com
```

Create with labels for tracking:

```bash
ops k8s secrets create-docker-registry gcr-auth \
  --server gcr.io \
  --username _json_key \
  --password "$(cat /path/to/gcr-key.json)" \
  --label registry=gcr \
  --label project=my-project
```

Create in production namespace:

```bash
ops k8s secrets create-docker-registry ecr-auth \
  -n production \
  --server 123456789.dkr.ecr.us-east-1.amazonaws.com \
  --username AWS \
  --password "$(aws ecr get-login-password)"
```

**Example Output:**

```text
Created Docker Registry Secret: my-reg
┌───────────┬─────────────────────────┐
│ Field     │ Value                   │
├───────────┼─────────────────────────┤
│ Name      │ my-reg                  │
│ Namespace │ default                 │
│ Type      │ kubernetes.io/dockercfg │
│ Status    │ Created                 │
│ Keys      │ 1 (.dockercfg)          │
│ Created   │ 2024-02-16T10:50:00Z    │
└───────────┴─────────────────────────┘
```

**Notes:**

- Use for image pull authentication in pod specs
- Support for Docker Hub, private registries, and cloud registries (GCR, ECR, ACR)
- Password can be token or actual password depending on registry
- Email is optional but can improve compatibility

---

### Delete Secret

Delete a Secret from the cluster.

```bash
ops k8s secrets delete my-secret
ops k8s secrets delete my-secret -n production
ops k8s secrets delete my-secret -f
```

**Options:**

| Option        | Short | Type   | Default             | Description              |
| ------------- | ----- | ------ | ------------------- | ------------------------ |
| `--namespace` | `-n`  | string | config or 'default' | Kubernetes namespace     |
| `--force`     | `-f`  | flag   | false               | Skip confirmation prompt |

**Example Output:**

```text
Are you sure you want to delete secret 'my-secret' in namespace 'default'? [y/N]: y
Secret 'my-secret' deleted
```

**Notes:**

- Requires confirmation unless `--force` is used
- Deletion may affect running pods that depend on this Secret
- Consider impact on applications using this Secret before deletion
- No recovery possible after deletion

---

## Persistent Volumes

Persistent Volumes are cluster-scoped storage resources that exist independently of pods.

### List Persistent Volumes

List all Persistent Volumes in the cluster.

```bash
ops k8s pvs list
ops k8s pvs list -l tier=fast
ops k8s pvs list -o yaml
```

**Options:**

| Option       | Short | Type   | Default | Description                      |
| ------------ | ----- | ------ | ------- | -------------------------------- |
| `--selector` | `-l`  | string | none    | Filter by labels                 |
| `--output`   | `-o`  | string | table   | Output format: table, json, yaml |

**Example Output:**

```text
Persistent Volumes
┌────────────┬──────────┬─────────────┬────────────────┬───────────┬──────────────┬─────┐
│ Name       │ Capacity │ Access Mode │ Reclaim Policy │ Status    │ StorageClass │ Age │
├────────────┼──────────┼─────────────┼────────────────┼───────────┼──────────────┼─────┤
│ pv-data-01 │ 100Gi    │ RWO         │ Retain         │ Bound     │ fast-ssd     │ 20d │
│ pv-data-02 │ 50Gi     │ RWO         │ Delete         │ Bound     │ standard     │ 15d │
│ pv-archive │ 500Gi    │ RWX         │ Retain         │ Available │ slow-hdd     │ 5d  │
└────────────┴──────────┴─────────────┴────────────────┴───────────┴──────────────┴─────┘
```

**Notes:**

- Cluster-scoped: not restricted by namespace
- Filter by labels to group PVs by tier or usage
- Status shows if PV is Bound to a PVC or Available
- Access modes: RWO (ReadWriteOnce), RWX (ReadWriteMany), ROX (ReadOnlyMany)

---

### Get Persistent Volume

Retrieve detailed information about a specific Persistent Volume.

```bash
ops k8s pvs get pv-data-01
ops k8s pvs get pv-data-01 -o json
```

**Options:**

| Option     | Short | Type   | Default | Description                      |
| ---------- | ----- | ------ | ------- | -------------------------------- |
| `--output` | `-o`  | string | table   | Output format: table, json, yaml |

**Example Output:**

```text
PersistentVolume: pv-data-01
┌────────────────┬──────────────────────┐
│ Field          │ Value                │
├────────────────┼──────────────────────┤
│ Name           │ pv-data-01           │
│ Capacity       │ 100Gi                │
│ Access Modes   │ ReadWriteOnce        │
│ Reclaim Policy │ Retain               │
│ Status         │ Bound                │
│ Claim          │ default / data-pvc   │
│ StorageClass   │ fast-ssd             │
│ Provisioner    │ ebs.csi.aws.com      │
│ Age            │ 20 days              │
│ Created        │ 2024-01-27T14:20:00Z │
└────────────────┴──────────────────────┘
```

**Notes:**

- Shows binding information if PV is claimed by a PVC
- Displays backend storage details (provider, provisioner)
- Useful for debugging storage availability issues

---

### Delete Persistent Volume

Delete a Persistent Volume from the cluster.

```bash
ops k8s pvs delete pv-data-01
ops k8s pvs delete pv-data-01 -f
```

**Options:**

| Option    | Short | Type | Default | Description              |
| --------- | ----- | ---- | ------- | ------------------------ |
| `--force` | `-f`  | flag | false   | Skip confirmation prompt |

**Example Output:**

```text
Are you sure you want to delete persistent volume 'pv-data-01'? [y/N]: y
PersistentVolume 'pv-data-01' deleted
```

**Notes:**

- Requires confirmation unless `--force` is used
- Cannot delete PV if it's bound to a PVC; must unbind first
- Reclaim policy determines what happens to the underlying storage
- Be cautious: data may be lost depending on reclaim policy

---

## Persistent Volume Claims

Persistent Volume Claims are namespace-scoped requests for storage by pods.

### List Persistent Volume Claims

List all Persistent Volume Claims in a namespace.

```bash
ops k8s pvcs list
ops k8s pvcs list -n production
ops k8s pvcs list -A
ops k8s pvcs list -l app=database
```

**Options:**

| Option             | Short | Type   | Default             | Description                      |
| ------------------ | ----- | ------ | ------------------- | -------------------------------- |
| `--namespace`      | `-n`  | string | config or 'default' | Kubernetes namespace             |
| `--all-namespaces` | `-A`  | flag   | false               | List across all namespaces       |
| `--selector`       | `-l`  | string | none                | Filter by labels                 |
| `--output`         | `-o`  | string | table               | Output format: table, json, yaml |

**Example Output:**

```text
Persistent Volume Claims
┌────────────┬────────────┬─────────┬────────┬──────────┬─────────────┬──────────────┬─────┐
│ Name       │ Namespace  │ Status  │ Volume │ Capacity │ Access Mode │ StorageClass │ Age │
├────────────┼────────────┼─────────┼────────┼──────────┼─────────────┼──────────────┼─────┤
│ data-pvc   │ default    │ Bound   │ pv-01  │ 50Gi     │ RWO         │ standard     │ 10d │
│ db-storage │ default    │ Bound   │ pv-02  │ 100Gi    │ RWO         │ fast-ssd     │ 5d  │
│ logs-pvc   │ production │ Pending │ -      │ 20Gi     │ RWX         │ shared       │ 1d  │
└────────────┴────────────┴─────────┴────────┴──────────┴─────────────┴──────────────┴─────┘
```

**Notes:**

- Status shows Pending (no PV available), Bound (to PV), or Lost
- Filter by labels to find PVCs for specific applications
- Use `--all-namespaces` to audit storage usage cluster-wide

---

### Get Persistent Volume Claim

Retrieve detailed information about a specific Persistent Volume Claim.

```bash
ops k8s pvcs get data-pvc
ops k8s pvcs get data-pvc -n production
ops k8s pvcs get data-pvc -o yaml
```

**Options:**

| Option        | Short | Type   | Default             | Description                      |
| ------------- | ----- | ------ | ------------------- | -------------------------------- |
| `--namespace` | `-n`  | string | config or 'default' | Kubernetes namespace             |
| `--output`    | `-o`  | string | table               | Output format: table, json, yaml |

**Example Output:**

```text
PVC: data-pvc
┌────────────────┬────────────────────────┐
│ Field          │ Value                  │
├────────────────┼────────────────────────┤
│ Name           │ data-pvc               │
│ Namespace      │ default                │
│ Status         │ Bound                  │
│ Volume         │ pv-data-01             │
│ Requested Size │ 50Gi                   │
│ Access Modes   │ ReadWriteOnce          │
│ StorageClass   │ standard               │
│ Mounted By     │ postgres-0, postgres-1 │
│ Age            │ 10 days                │
│ Created        │ 2024-02-06T10:15:00Z   │
└────────────────┴────────────────────────┘
```

**Notes:**

- Shows which pods are currently using this PVC
- Status indicates if claim is satisfied by available PV
- Useful for debugging storage allocation issues

---

### Create Persistent Volume Claim

Create a new Persistent Volume Claim to request storage.

```bash
ops k8s pvcs create data-pvc --storage 10Gi --access-mode ReadWriteOnce
ops k8s pvcs create db-storage -n production --storage 100Gi --storage-class fast-ssd
```

**Options:**

| Option            | Short | Type   | Default             | Description                                |
| ----------------- | ----- | ------ | ------------------- | ------------------------------------------ |
| `--namespace`     | `-n`  | string | config or 'default' | Kubernetes namespace                       |
| `--storage-class` |       | string | none                | StorageClass name for dynamic provisioning |
| `--access-mode`   |       | string | ReadWriteOnce       | Access mode (repeatable)                   |
| `--storage`       |       | string | 1Gi                 | Storage size (e.g., 10Gi, 100Mi)           |
| `--label`         | `-l`  | string | none                | Label (key=value, repeatable)              |
| `--output`        | `-o`  | string | table               | Output format: table, json, yaml           |

**Examples:**

Create basic PVC:

```bash
ops k8s pvcs create app-data \
  --storage 20Gi \
  --access-mode ReadWriteOnce
```

Create with specific StorageClass:

```bash
ops k8s pvcs create db-storage \
  --storage 100Gi \
  --storage-class fast-ssd \
  --access-mode ReadWriteOnce
```

Create with labels for organization:

```bash
ops k8s pvcs create cache-pvc \
  --storage 50Gi \
  --storage-class standard \
  --label app=redis \
  --label env=production \
  --label tier=cache
```

Create in specific namespace:

```bash
ops k8s pvcs create logs-pvc \
  -n production \
  --storage 500Gi \
  --storage-class slow-ssd \
  --access-mode ReadWriteMany
```

**Example Output:**

```text
Created PVC: data-pvc
┌──────────────┬──────────────────────┐
│ Field        │ Value                │
├──────────────┼──────────────────────┤
│ Name         │ data-pvc             │
│ Namespace    │ default              │
│ Status       │ Pending              │
│ Requested    │ 10Gi                 │
│ Access Modes │ ReadWriteOnce        │
│ StorageClass │ standard             │
│ Created      │ 2024-02-16T11:00:00Z │
└──────────────┴──────────────────────┘
```

**Notes:**

- Without `--storage-class`, uses cluster default or manual PV matching
- Multiple access modes can be specified with repeating `--access-mode`
- Size units: Ki, Mi, Gi, Ti, Pi, Ei (binary) or k, M, G, T, P, E (decimal)
- With dynamic provisioning, PVC automatically provisions underlying storage

---

### Delete Persistent Volume Claim

Delete a Persistent Volume Claim from the cluster.

```bash
ops k8s pvcs delete data-pvc
ops k8s pvcs delete data-pvc -n production
ops k8s pvcs delete data-pvc -f
```

**Options:**

| Option        | Short | Type   | Default             | Description              |
| ------------- | ----- | ------ | ------------------- | ------------------------ |
| `--namespace` | `-n`  | string | config or 'default' | Kubernetes namespace     |
| `--force`     | `-f`  | flag   | false               | Skip confirmation prompt |

**Example Output:**

```text
Are you sure you want to delete PVC 'data-pvc' in namespace 'default'? [y/N]: y
PVC 'data-pvc' deleted
```

**Notes:**

- Requires confirmation unless `--force` is used
- Cannot delete if pods are currently using the PVC
- May trigger deletion of underlying PV depending on reclaim policy
- Data may be lost; ensure backups exist before deletion

---

## Storage Classes

Storage Classes define how storage is provisioned and managed in the cluster.

### List Storage Classes

List all Storage Classes available in the cluster.

```bash
ops k8s storage-classes list
ops k8s storage-classes list -o json
```

**Options:**

| Option     | Short | Type   | Default | Description                      |
| ---------- | ----- | ------ | ------- | -------------------------------- |
| `--output` | `-o`  | string | table   | Output format: table, json, yaml |

**Example Output:**

```text
Storage Classes
┌──────────┬───────────────────┬────────────────┬──────────────┬──────────────┬─────┐
│ Name     │ Provisioner       │ Reclaim Policy │ Binding Mode │ Allow Expand │ Age │
├──────────┼───────────────────┼────────────────┼──────────────┼──────────────┼─────┤
│ standard │ pd.csi.storage... │ Delete         │ Immediate    │ True         │ 30d │
│ fast-ssd │ pd.csi.storage... │ Delete         │ Immediate    │ True         │ 20d │
│ slow-hdd │ pd.csi.storage... │ Delete         │ WaitForFirst │ False        │ 15d │
└──────────┴───────────────────┴────────────────┴──────────────┴──────────────┴─────┘
```

**Notes:**

- Cluster-scoped: not restricted by namespace
- Provisioner determines the backend storage system
- Binding mode affects when PVs are provisioned
- Allow Expansion indicates if PVC can grow after creation

---

### Get Storage Class

Retrieve detailed information about a specific Storage Class.

```bash
ops k8s storage-classes get standard
ops k8s storage-classes get fast-ssd -o yaml
```

**Options:**

| Option     | Short | Type   | Default | Description                      |
| ---------- | ----- | ------ | ------- | -------------------------------- |
| `--output` | `-o`  | string | table   | Output format: table, json, yaml |

**Example Output:**

```text
StorageClass: standard
┌────────────────────────┬───────────────────────┐
│ Field                  │ Value                 │
├────────────────────────┼───────────────────────┤
│ Name                   │ standard              │
│ Provisioner            │ pd.csi.storage.gke.io │
│ Reclaim Policy         │ Delete                │
│ Binding Mode           │ Immediate             │
│ Allow Volume Expansion │ True                  │
│ Parameters             │ type: pd-standard     │
│ Age                    │ 30 days               │
│ Created                │ 2024-01-17T09:00:00Z  │
└────────────────────────┴───────────────────────┘
```

**Notes:**

- Shows provisioning parameters specific to the backend
- Binding mode affects PV creation timing (Immediate vs WaitForFirstConsumer)
- Reclaim policy determines what happens to PV when PVC is deleted
- Use to understand available storage options for PVCs

---

## Troubleshooting

| Issue                                 | Solution                                                                 |
| ------------------------------------- | ------------------------------------------------------------------------ |
| "configmap not found"                 | Verify namespace with `-n` flag. Use `list` to find exact name. Check if |
| "secret not found"                    | Check namespace and name spelling. Use `list -A` to search all           |
| "PVC stuck in Pending"                | Check available PVs with `ops k8s pvs list`. Verify StorageClass         |
| "Cannot delete PVC in use"            | Identify pods mounting PVC with                                          |
| "Cannot delete PV if bound"           | Delete PVC first. Verify reclaim                                         |
| "Insufficient storage"                | List PVs to see capacity. Check quota                                    |
| "Access denied when creating secrets" | Verify RBAC role includes `create`                                       |
| "TLS secret creation fails"           | Verify cert and key files exist and are readable.                        |
| "Docker registry secret fails"        | Verify credentials are correct. Confirm registry server                  |
| "Data size exceeds ConfigMap limit"   | ConfigMap limit is 1MB. Split data across multiple ConfigMaps.           |

---

## See Also

- [RBAC Commands](./rbac.md) - Manage access control to secrets and configurations
- [Jobs Commands](./jobs.md) - Run jobs that use ConfigMaps and Secrets
- [Kubernetes Plugin Index](../index.md) - Complete plugin documentation
- [Examples](../examples.md) - Common configuration and storage patterns
- [Ecosystem](../ecosystem/) - Related Kubernetes tools and integrations
- [TUI Interface](../tui.md) - Terminal UI for visualizing resources
