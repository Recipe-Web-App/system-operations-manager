# Kubernetes Plugin > Ecosystem > cert-manager

[< Back to Index](../index.md) | [Commands](../commands/) | [Ecosystem](./) | [TUI](../tui.md) | [Examples](../examples.md)

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Detection](#detection)
- [Configuration](#configuration)
- [Command Reference](#command-reference)
  - [Certificates](#certificates)
  - [Issuers](#issuers)
  - [Cluster Issuers](#cluster-issuers)
  - [ACME Helpers](#acme-helpers)
  - [Certificate Requests](#certificate-requests)
  - [ACME Challenges](#acme-challenges)
- [Integration Examples](#integration-examples)
- [Troubleshooting](#troubleshooting)
- [See Also](#see-also)

---

## Overview

cert-manager is a powerful Kubernetes certificate management tool that automates the provisioning and renewal of TLS
certificates from various issuers including Let's Encrypt, Vault, and internal certificate authorities. It simplifies
SSL/TLS certificate lifecycle management in Kubernetes.

The Kubernetes plugin provides comprehensive CLI integration with cert-manager through the `certs` command family. This
integration enables you to:

- Create and manage Certificate resources with automatic renewal
- Define Issuers and ClusterIssuers for certificate provisioning
- Configure ACME providers like Let's Encrypt with helper commands
- View and troubleshoot ACME challenges and certificate requests
- Monitor certificate status, expiry, and renewal information
- Manage certificates across namespaces or cluster-wide

cert-manager is built on Kubernetes CustomResourceDefinitions (CRDs), providing native Kubernetes integration. The
plugin detects cert-manager availability by checking for the presence of Certificate CRDs in your cluster.

## Prerequisites

To use the cert-manager integration, you need:

1. **cert-manager Controller**: Install cert-manager in your cluster

   ```bash
   kubectl create namespace cert-manager
   kubectl apply -f https://github.com/cert-manager/cert-manager/releases/latest/download/cert-manager.yaml
   ```

2. **Kubernetes Access**: Valid kubeconfig with permissions to create and manage Certificate, Issuer, ClusterIssuer,
   CertificateRequest, and Challenge resources

3. **CRDs**: cert-manager CRDs must be installed (automatically installed with the controller)

4. **For Let's Encrypt**: An email address for ACME registration and domain DNS access

5. **Version Requirements**:
   - cert-manager: 1.3 or later
   - Kubernetes: 1.16 or later
   - kubectl: 1.16 or later

## Detection

The plugin automatically detects whether cert-manager is available in your cluster by checking for the presence of the
`Certificate` CRD. Verify detection with:

```bash
ops k8s certs cert list
```

If cert-manager is not installed, you'll receive a clear error message indicating the Certificate CRD is not found.

## Configuration

cert-manager integration uses the standard Kubernetes plugin configuration. No additional ecosystem-specific
configuration is required beyond standard Kubernetes access settings.

Optional configuration for default namespaces:

```yaml
# In your ops config
kubernetes:
  default_namespace: default
  cert_manager_namespace: cert-manager
```

---

## Command Reference

### Certificates

#### `ops k8s certs cert list`

List all Certificates in a namespace.

```bash
ops k8s certs cert list [OPTIONS]
```

**Arguments:**
None

**Options:**

| Option        | Short | Type   | Default   | Description                             |
| ------------- | ----- | ------ | --------- | --------------------------------------- |
| `--namespace` | `-n`  | string | `default` | Kubernetes namespace to query           |
| `--selector`  | `-l`  | string | None      | Label selector filter (e.g., 'app=web') |
| `--output`    | `-o`  | string | `table`   | Output format: table, json, or yaml     |

**Example Output:**

```text
Certificates

NAME                NAMESPACE   SECRET              ISSUER              DNS NAMES                         READY  RENEWAL              AGE
example-com-tls     production  example-com-cert    letsencrypt-prod    example.com,www.example.com      True   2024-05-17T10:30Z    89d
api-internal-cert   production  api-internal-tls    ca-issuer           api.internal.example.com         True   2024-04-20T08:15Z    2d 12h
staging-cert        staging     staging-cert-tls    letsencrypt-staging staging.example.com              False  2024-03-15T14:45Z    15d
```

**Examples:**

```bash
# List certificates in default namespace
ops k8s certs cert list

# List in production namespace
ops k8s certs cert list -n production

# Filter by label
ops k8s certs cert list -l app=web -n production

# Get JSON output
ops k8s certs cert list -o json

# Get YAML backup
ops k8s certs cert list -o yaml
```

---

#### `ops k8s certs cert get`

Get detailed information about a specific Certificate.

```bash
ops k8s certs cert get <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description               |
| -------- | -------- | ------------------------- |
| `name`   | Yes      | Certificate resource name |

**Options:**

| Option        | Short | Type   | Default   | Description                         |
| ------------- | ----- | ------ | --------- | ----------------------------------- |
| `--namespace` | `-n`  | string | `default` | Kubernetes namespace                |
| `--output`    | `-o`  | string | `table`   | Output format: table, json, or yaml |

**Example Output:**

```text
Certificate: example-com-tls

name               example-com-tls
namespace          production
secret_name        example-com-cert
issuer_name        letsencrypt-prod
dns_names          example.com, www.example.com
ready              True
renewal_time       2024-05-17T10:30Z
age                89d
```

**Examples:**

```bash
# Get certificate details
ops k8s certs cert get example-com-tls

# Get in production namespace
ops k8s certs cert get example-com-tls -n production

# Get full YAML definition
ops k8s certs cert get example-com-tls -o yaml

# Get JSON for script processing
ops k8s certs cert get example-com-tls -o json
```

---

#### `ops k8s certs cert create`

Create a new Certificate resource.

```bash
ops k8s certs cert create <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description               |
| -------- | -------- | ------------------------- |
| `name`   | Yes      | Certificate resource name |

**Options:**

| Option           | Short | Type   | Default   | Description                                             |
| ---------------- | ----- | ------ | --------- | ------------------------------------------------------- |
| `--namespace`    | `-n`  | string | `default` | Kubernetes namespace                                    |
| `--secret-name`  |       | string | Required  | Name of Secret where certificate will be stored         |
| `--issuer-name`  |       | string | Required  | Issuer or ClusterIssuer name                            |
| `--dns-name`     |       | string | Required  | DNS names/SANs (repeatable)                             |
| `--issuer-kind`  |       | string | `Issuer`  | Issuer kind: Issuer or ClusterIssuer                    |
| `--common-name`  |       | string | None      | Certificate Common Name (CN)                            |
| `--duration`     |       | string | None      | Certificate validity duration (e.g., 2160h for 90 days) |
| `--renew-before` |       | string | None      | Renewal window (e.g., 360h for 15 days before expiry)   |
| `--label`        | `-l`  | string | None      | Labels as key=value (repeatable)                        |
| `--output`       | `-o`  | string | `table`   | Output format: table, json, or yaml                     |

**Duration Format:**

Go duration format (examples):

- `2160h` = 90 days
- `4320h` = 180 days
- `8760h` = 1 year

**Example Output:**

```text
Created Certificate: example-com-tls

metadata:
  name: example-com-tls
  namespace: production
spec:
  secretName: example-com-cert
  issuerRef:
    name: letsencrypt-prod
    kind: Issuer
  dnsNames:
  - example.com
  - www.example.com
  duration: 2160h
  renewBefore: 360h
```

**Examples:**

```bash
# Create certificate for Let's Encrypt
ops k8s certs cert create example-com-tls \
  --secret-name example-com-cert \
  --issuer-name letsencrypt-prod \
  --dns-name example.com \
  --dns-name www.example.com

# Create with custom duration and renewal window
ops k8s certs cert create internal-api-cert \
  --secret-name internal-api-tls \
  --issuer-name ca-issuer \
  --dns-name api.internal.example.com \
  --duration 8760h \
  --renew-before 720h

# Create with ClusterIssuer
ops k8s certs cert create global-cert \
  --secret-name global-tls \
  --issuer-name global-ca \
  --issuer-kind ClusterIssuer \
  --dns-name "*.example.com"

# Create with labels
ops k8s certs cert create app-cert \
  --secret-name app-tls \
  --issuer-name letsencrypt-prod \
  --dns-name app.example.com \
  --label app=web \
  --label team=platform

# Create in specific namespace
ops k8s certs cert create staging-cert \
  --secret-name staging-tls \
  --issuer-name letsencrypt-staging \
  --dns-name staging.example.com \
  -n staging
```

---

#### `ops k8s certs cert delete`

Delete a Certificate resource.

```bash
ops k8s certs cert delete <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description               |
| -------- | -------- | ------------------------- |
| `name`   | Yes      | Certificate resource name |

**Options:**

| Option        | Short | Type    | Default   | Description              |
| ------------- | ----- | ------- | --------- | ------------------------ |
| `--namespace` | `-n`  | string  | `default` | Kubernetes namespace     |
| `--force`     | `-f`  | boolean | False     | Skip confirmation prompt |

**Example Output:**

```text
Certificate 'example-com-tls' deleted
```

**Examples:**

```bash
# Delete certificate with confirmation
ops k8s certs cert delete example-com-tls

# Delete without confirmation
ops k8s certs cert delete example-com-tls --force

# Delete in production namespace
ops k8s certs cert delete example-com-tls -n production --force
```

---

#### `ops k8s certs cert status`

Show detailed status information for a Certificate.

```bash
ops k8s certs cert status <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description               |
| -------- | -------- | ------------------------- |
| `name`   | Yes      | Certificate resource name |

**Options:**

| Option        | Short | Type   | Default   | Description                         |
| ------------- | ----- | ------ | --------- | ----------------------------------- |
| `--namespace` | `-n`  | string | `default` | Kubernetes namespace                |
| `--output`    | `-o`  | string | `table`   | Output format: table, json, or yaml |

**Example Output:**

```text
Certificate Status: example-com-tls

ready                True
notBefore           2023-02-16T10:30:00Z
notAfter            2024-05-17T10:30:00Z
renewalTime         2024-05-17T10:30:00Z
daysRemaining       89
conditions:
  - type: Issuing
    status: False
    lastTransitionTime: 2023-02-16T10:35:00Z
  - type: Ready
    status: True
    message: Certificate is up to date and has not expired
```

**Examples:**

```bash
# Get certificate status
ops k8s certs cert status example-com-tls

# Get status in production namespace
ops k8s certs cert status example-com-tls -n production

# Get status as JSON
ops k8s certs cert status example-com-tls -o json
```

---

#### `ops k8s certs cert renew`

Force renewal of a Certificate.

```bash
ops k8s certs cert renew <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description               |
| -------- | -------- | ------------------------- |
| `name`   | Yes      | Certificate resource name |

**Options:**

| Option        | Short | Type   | Default   | Description          |
| ------------- | ----- | ------ | --------- | -------------------- |
| `--namespace` | `-n`  | string | `default` | Kubernetes namespace |

**Example Output:**

```text
Certificate 'example-com-tls' renewal triggered
```

**Examples:**

```bash
# Trigger certificate renewal
ops k8s certs cert renew example-com-tls

# Renew in production namespace
ops k8s certs cert renew example-com-tls -n production
```

---

### Issuers

#### `ops k8s certs issuer list`

List all Issuers in a namespace.

```bash
ops k8s certs issuer list [OPTIONS]
```

**Arguments:**
None

**Options:**

| Option        | Short | Type   | Default   | Description                         |
| ------------- | ----- | ------ | --------- | ----------------------------------- |
| `--namespace` | `-n`  | string | `default` | Kubernetes namespace                |
| `--selector`  | `-l`  | string | None      | Label selector filter               |
| `--output`    | `-o`  | string | `table`   | Output format: table, json, or yaml |

**Example Output:**

```text
Issuers

NAME                  NAMESPACE     TYPE       ACME SERVER                          READY  AGE
letsencrypt-staging   production    acme       https://acme-staging-v02.api...     True   180d
letsencrypt-prod      production    acme       https://acme-v02.api.letsenc...     True   180d
ca-issuer             production    ca         N/A                                  True   90d
self-signed           production    selfSigned N/A                                  True   45d
```

**Examples:**

```bash
# List issuers in default namespace
ops k8s certs issuer list

# List in production namespace
ops k8s certs issuer list -n production

# Filter by label
ops k8s certs issuer list -l app=web

# Get JSON output
ops k8s certs issuer list -o json
```

---

#### `ops k8s certs issuer get`

Get details of a specific Issuer.

```bash
ops k8s certs issuer get <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description          |
| -------- | -------- | -------------------- |
| `name`   | Yes      | Issuer resource name |

**Options:**

| Option        | Short | Type   | Default   | Description                         |
| ------------- | ----- | ------ | --------- | ----------------------------------- |
| `--namespace` | `-n`  | string | `default` | Kubernetes namespace                |
| `--output`    | `-o`  | string | `table`   | Output format: table, json, or yaml |

**Example Output:**

```text
Issuer: letsencrypt-prod

name           letsencrypt-prod
namespace      production
issuer_type    acme
acme_server    https://acme-v02.api.letsencrypt.org/directory
ready          True
age            180d
```

**Examples:**

```bash
# Get issuer details
ops k8s certs issuer get letsencrypt-prod

# Get in production namespace
ops k8s certs issuer get letsencrypt-prod -n production

# Get full YAML definition
ops k8s certs issuer get letsencrypt-prod -o yaml
```

---

#### `ops k8s certs issuer create`

Create a new Issuer resource.

```bash
ops k8s certs issuer create <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description          |
| -------- | -------- | -------------------- |
| `name`   | Yes      | Issuer resource name |

**Options:**

| Option        | Short | Type   | Default   | Description                              |
| ------------- | ----- | ------ | --------- | ---------------------------------------- |
| `--namespace` | `-n`  | string | `default` | Kubernetes namespace                     |
| `--type`      |       | string | Required  | Issuer type: acme, ca, selfSigned, vault |
| `--config`    |       | string | Required  | Type-specific config as JSON object      |
| `--label`     | `-l`  | string | None      | Labels as key=value (repeatable)         |
| `--output`    | `-o`  | string | `table`   | Output format: table, json, or yaml      |

**Issuer Type Configurations:**

**Self-Signed:**

```json
{}
```

**CA (Certificate Authority):**

```json
{ "secretName": "ca-key-pair" }
```

**ACME (Let's Encrypt - use helper instead):**

```json
{
  "server": "https://acme-v02.api.letsencrypt.org/directory",
  "email": "admin@example.com",
  "privateKeySecretRef": { "name": "letsencrypt-key" },
  "solvers": [{ "http01": { "ingress": { "class": "nginx" } } }]
}
```

**Example Output:**

```text
Created Issuer: ca-issuer

metadata:
  name: ca-issuer
  namespace: production
spec:
  ca:
    secretName: ca-key-pair
```

**Examples:**

```bash
# Create self-signed issuer
ops k8s certs issuer create self-signed \
  --type selfSigned \
  --config '{}'

# Create CA issuer
ops k8s certs issuer create my-ca \
  --type ca \
  --config '{"secretName":"ca-key-pair"}'

# Create with labels
ops k8s certs issuer create internal-ca \
  --type ca \
  --config '{"secretName":"internal-ca-pair"}' \
  --label app=infrastructure \
  --label env=production

# Create in specific namespace
ops k8s certs issuer create staging-ca \
  --type ca \
  --config '{"secretName":"staging-ca-pair"}' \
  -n staging
```

---

#### `ops k8s certs issuer delete`

Delete an Issuer resource.

```bash
ops k8s certs issuer delete <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description          |
| -------- | -------- | -------------------- |
| `name`   | Yes      | Issuer resource name |

**Options:**

| Option        | Short | Type    | Default   | Description              |
| ------------- | ----- | ------- | --------- | ------------------------ |
| `--namespace` | `-n`  | string  | `default` | Kubernetes namespace     |
| `--force`     | `-f`  | boolean | False     | Skip confirmation prompt |

**Example Output:**

```text
Issuer 'my-issuer' deleted
```

**Examples:**

```bash
# Delete issuer with confirmation
ops k8s certs issuer delete my-issuer

# Delete without confirmation
ops k8s certs issuer delete my-issuer --force

# Delete in production namespace
ops k8s certs issuer delete my-issuer -n production --force
```

---

#### `ops k8s certs issuer status`

Show status of an Issuer.

```bash
ops k8s certs issuer status <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description          |
| -------- | -------- | -------------------- |
| `name`   | Yes      | Issuer resource name |

**Options:**

| Option        | Short | Type   | Default   | Description                         |
| ------------- | ----- | ------ | --------- | ----------------------------------- |
| `--namespace` | `-n`  | string | `default` | Kubernetes namespace                |
| `--output`    | `-o`  | string | `table`   | Output format: table, json, or yaml |

**Example Output:**

```text
Issuer Status: letsencrypt-prod

ready          True
conditions:
  - type: Ready
    status: True
    message: Signing CA verified
lastChecked    2024-02-16T15:30:00Z
```

**Examples:**

```bash
# Get issuer status
ops k8s certs issuer status letsencrypt-prod

# Get in production namespace
ops k8s certs issuer status letsencrypt-prod -n production

# Get status as JSON
ops k8s certs issuer status letsencrypt-prod -o json
```

---

### Cluster Issuers

#### `ops k8s certs clusterissuer list`

List all ClusterIssuers (cluster-scoped).

```bash
ops k8s certs clusterissuer list [OPTIONS]
```

**Arguments:**
None

**Options:**

| Option       | Short | Type   | Default | Description                         |
| ------------ | ----- | ------ | ------- | ----------------------------------- |
| `--selector` | `-l`  | string | None    | Label selector filter               |
| `--output`   | `-o`  | string | `table` | Output format: table, json, or yaml |

**Example Output:**

```text
Cluster Issuers

NAME                 TYPE         ACME SERVER                     READY  AGE
letsencrypt-staging  acme         https://acme-staging-v02...     True   200d
letsencrypt-prod     acme         https://acme-v02.api.le...      True   200d
internal-ca          ca           N/A                             True   150d
```

**Examples:**

```bash
# List all cluster issuers
ops k8s certs clusterissuer list

# Filter by label
ops k8s certs clusterissuer list -l app=infrastructure

# Get JSON output
ops k8s certs clusterissuer list -o json
```

---

#### `ops k8s certs clusterissuer get`

Get details of a specific ClusterIssuer.

```bash
ops k8s certs clusterissuer get <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                 |
| -------- | -------- | --------------------------- |
| `name`   | Yes      | ClusterIssuer resource name |

**Options:**

| Option     | Short | Type   | Default | Description                         |
| ---------- | ----- | ------ | ------- | ----------------------------------- |
| `--output` | `-o`  | string | `table` | Output format: table, json, or yaml |

**Example Output:**

```text
ClusterIssuer: letsencrypt-prod

name           letsencrypt-prod
issuer_type    acme
acme_server    https://acme-v02.api.letsencrypt.org/directory
ready          True
age            200d
```

**Examples:**

```bash
# Get cluster issuer details
ops k8s certs clusterissuer get letsencrypt-prod

# Get full YAML definition
ops k8s certs clusterissuer get letsencrypt-prod -o yaml

# Get JSON output
ops k8s certs clusterissuer get letsencrypt-prod -o json
```

---

#### `ops k8s certs clusterissuer create`

Create a new ClusterIssuer resource.

```bash
ops k8s certs clusterissuer create <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                 |
| -------- | -------- | --------------------------- |
| `name`   | Yes      | ClusterIssuer resource name |

**Options:**

| Option     | Short | Type   | Default  | Description                              |
| ---------- | ----- | ------ | -------- | ---------------------------------------- |
| `--type`   |       | string | Required | Issuer type: acme, ca, selfSigned, vault |
| `--config` |       | string | Required | Type-specific config as JSON object      |
| `--label`  | `-l`  | string | None     | Labels as key=value (repeatable)         |
| `--output` | `-o`  | string | `table`  | Output format: table, json, or yaml      |

**Example Output:**

```text
Created ClusterIssuer: global-ca

metadata:
  name: global-ca
spec:
  ca:
    secretName: global-ca-key-pair
```

**Examples:**

```bash
# Create self-signed cluster issuer
ops k8s certs clusterissuer create self-signed \
  --type selfSigned \
  --config '{}'

# Create CA cluster issuer
ops k8s certs clusterissuer create global-ca \
  --type ca \
  --config '{"secretName":"global-ca-key-pair"}'

# Create with labels
ops k8s certs clusterissuer create cluster-ca \
  --type ca \
  --config '{"secretName":"cluster-ca-pair"}' \
  --label scope=cluster-wide
```

---

#### `ops k8s certs clusterissuer delete`

Delete a ClusterIssuer.

```bash
ops k8s certs clusterissuer delete <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                 |
| -------- | -------- | --------------------------- |
| `name`   | Yes      | ClusterIssuer resource name |

**Options:**

| Option    | Short | Type    | Default | Description              |
| --------- | ----- | ------- | ------- | ------------------------ |
| `--force` | `-f`  | boolean | False   | Skip confirmation prompt |

**Example Output:**

```text
ClusterIssuer 'global-ca' deleted
```

**Examples:**

```bash
# Delete cluster issuer with confirmation
ops k8s certs clusterissuer delete global-ca

# Delete without confirmation
ops k8s certs clusterissuer delete global-ca --force
```

---

#### `ops k8s certs clusterissuer status`

Show status of a ClusterIssuer.

```bash
ops k8s certs clusterissuer status <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                 |
| -------- | -------- | --------------------------- |
| `name`   | Yes      | ClusterIssuer resource name |

**Options:**

| Option     | Short | Type   | Default | Description                         |
| ---------- | ----- | ------ | ------- | ----------------------------------- |
| `--output` | `-o`  | string | `table` | Output format: table, json, or yaml |

**Example Output:**

```text
ClusterIssuer Status: letsencrypt-prod

ready          True
conditions:
  - type: Ready
    status: True
    message: ACME account registered
lastChecked    2024-02-16T15:30:00Z
```

**Examples:**

```bash
# Get cluster issuer status
ops k8s certs clusterissuer status letsencrypt-prod

# Get status as JSON
ops k8s certs clusterissuer status letsencrypt-prod -o json
```

---

### ACME Helpers

#### `ops k8s certs acme create-issuer`

Create an ACME Issuer (e.g., Let's Encrypt) - namespaced version.

```bash
ops k8s certs acme create-issuer <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description          |
| -------- | -------- | -------------------- |
| `name`   | Yes      | Issuer resource name |

**Options:**

| Option                 | Short | Type    | Default    | Description                                       |
| ---------------------- | ----- | ------- | ---------- | ------------------------------------------------- |
| `--namespace`          | `-n`  | string  | `default`  | Kubernetes namespace                              |
| `--email`              |       | string  | Required   | Email for ACME registration                       |
| `--server`             |       | string  | LE Staging | ACME server URL                                   |
| `--production`         |       | boolean | False      | Use Let's Encrypt production (overrides --server) |
| `--private-key-secret` |       | string  | Empty      | Secret name for ACME account key                  |
| `--solver-type`        |       | string  | `http01`   | Solver type: http01 or dns01                      |
| `--ingress-class`      |       | string  | None       | Ingress class for HTTP-01 solver                  |
| `--label`              | `-l`  | string  | None       | Labels as key=value (repeatable)                  |
| `--output`             | `-o`  | string  | `table`    | Output format: table, json, or yaml               |

**Example Output:**

```text
Created ACME Issuer: letsencrypt-prod

metadata:
  name: letsencrypt-prod
  namespace: production
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-prod-key
    solvers:
    - http01:
        ingress:
          class: nginx
```

**Examples:**

```bash
# Create staging ACME issuer
ops k8s certs acme create-issuer letsencrypt-staging \
  --email admin@example.com

# Create production ACME issuer
ops k8s certs acme create-issuer letsencrypt-prod \
  --email admin@example.com \
  --production \
  --ingress-class nginx

# Create with DNS-01 solver for wildcard certs
ops k8s certs acme create-issuer letsencrypt-prod \
  --email admin@example.com \
  --production \
  --solver-type dns01

# Create in specific namespace
ops k8s certs acme create-issuer letsencrypt-prod \
  --email admin@example.com \
  --production \
  -n production
```

---

#### `ops k8s certs acme create-clusterissuer`

Create an ACME ClusterIssuer (cluster-scoped).

```bash
ops k8s certs acme create-clusterissuer <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                 |
| -------- | -------- | --------------------------- |
| `name`   | Yes      | ClusterIssuer resource name |

**Options:**

| Option                 | Short | Type    | Default    | Description                         |
| ---------------------- | ----- | ------- | ---------- | ----------------------------------- |
| `--email`              |       | string  | Required   | Email for ACME registration         |
| `--server`             |       | string  | LE Staging | ACME server URL                     |
| `--production`         |       | boolean | False      | Use Let's Encrypt production        |
| `--private-key-secret` |       | string  | Empty      | Secret name for ACME account key    |
| `--solver-type`        |       | string  | `http01`   | Solver type: http01 or dns01        |
| `--ingress-class`      |       | string  | None       | Ingress class for HTTP-01 solver    |
| `--label`              | `-l`  | string  | None       | Labels as key=value (repeatable)    |
| `--output`             | `-o`  | string  | `table`    | Output format: table, json, or yaml |

**Example Output:**

```text
Created ACME ClusterIssuer: letsencrypt-prod

metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-prod-key
```

**Examples:**

```bash
# Create production cluster issuer
ops k8s certs acme create-clusterissuer letsencrypt-prod \
  --email admin@example.com \
  --production \
  --ingress-class nginx

# Create with custom ACME server
ops k8s certs acme create-clusterissuer custom-acme \
  --email admin@example.com \
  --server https://custom-acme.example.com/directory

# Create staging for testing
ops k8s certs acme create-clusterissuer letsencrypt-staging \
  --email admin@example.com
```

---

### Certificate Requests

#### `ops k8s certs request list`

List all CertificateRequests in a namespace (read-only).

```bash
ops k8s certs request list [OPTIONS]
```

**Arguments:**
None

**Options:**

| Option        | Short | Type   | Default   | Description                         |
| ------------- | ----- | ------ | --------- | ----------------------------------- |
| `--namespace` | `-n`  | string | `default` | Kubernetes namespace                |
| `--selector`  | `-l`  | string | None      | Label selector filter               |
| `--output`    | `-o`  | string | `table`   | Output format: table, json, or yaml |

**Example Output:**

```text
Certificate Requests

NAME                                   NAMESPACE     ISSUER              KIND       READY  APPROVED  AGE
example-com-tls-1234567890            production    letsencrypt-prod    Issuer     True   True      1h 30m
api-cert-request-xyz789               production    ca-issuer           Issuer     True   True      2h 45m
staging-cert-request-abc123           staging       letsencrypt-staging Issuer     False  False     5m
```

**Examples:**

```bash
# List certificate requests
ops k8s certs request list

# List in production namespace
ops k8s certs request list -n production

# Filter by issuer
ops k8s certs request list -l issuer=letsencrypt-prod

# Get JSON output
ops k8s certs request list -o json
```

---

#### `ops k8s certs request get`

Get details of a specific CertificateRequest.

```bash
ops k8s certs request get <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                      |
| -------- | -------- | -------------------------------- |
| `name`   | Yes      | CertificateRequest resource name |

**Options:**

| Option        | Short | Type   | Default   | Description                         |
| ------------- | ----- | ------ | --------- | ----------------------------------- |
| `--namespace` | `-n`  | string | `default` | Kubernetes namespace                |
| `--output`    | `-o`  | string | `table`   | Output format: table, json, or yaml |

**Example Output:**

```text
CertificateRequest: example-com-tls-1234567890

name             example-com-tls-1234567890
namespace        production
issuer_name      letsencrypt-prod
issuer_kind      Issuer
ready            True
approved         True
age              1h 30m
```

**Examples:**

```bash
# Get certificate request details
ops k8s certs request get example-com-tls-1234567890

# Get in production namespace
ops k8s certs request get example-com-tls-1234567890 -n production

# Get full YAML definition
ops k8s certs request get example-com-tls-1234567890 -o yaml
```

---

### ACME Challenges

#### `ops k8s certs challenge list`

List all ACME Challenges in a namespace.

```bash
ops k8s certs challenge list [OPTIONS]
```

**Arguments:**
None

**Options:**

| Option        | Short | Type   | Default   | Description                         |
| ------------- | ----- | ------ | --------- | ----------------------------------- |
| `--namespace` | `-n`  | string | `default` | Kubernetes namespace                |
| `--selector`  | `-l`  | string | None      | Label selector filter               |
| `--output`    | `-o`  | string | `table`   | Output format: table, json, or yaml |

**Example Output:**

```text
ACME Challenges

NAME                                      NAMESPACE     TYPE     DOMAIN               STATE       PRESENTED  AGE
example-com-tls-1234567890-0            production    http-01  example.com          valid       True       15m
www-example-com-tls-1234567890-1        production    http-01  www.example.com      valid       True       15m
api-cert-challenge-abc123               production    dns-01   api.example.com      pending     False      2m
```

**Examples:**

```bash
# List ACME challenges
ops k8s certs challenge list

# List in cert-manager namespace
ops k8s certs challenge list -n cert-manager

# Filter by state
ops k8s certs challenge list -l certmanager.k8s.io/challenge-key

# Get JSON output
ops k8s certs challenge list -o json
```

---

#### `ops k8s certs challenge get`

Get details of a specific ACME Challenge.

```bash
ops k8s certs challenge get <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description             |
| -------- | -------- | ----------------------- |
| `name`   | Yes      | Challenge resource name |

**Options:**

| Option        | Short | Type   | Default   | Description                         |
| ------------- | ----- | ------ | --------- | ----------------------------------- |
| `--namespace` | `-n`  | string | `default` | Kubernetes namespace                |
| `--output`    | `-o`  | string | `table`   | Output format: table, json, or yaml |

**Example Output:**

```text
Challenge: example-com-tls-1234567890-0

name             example-com-tls-1234567890-0
namespace        production
challenge_type   http-01
dns_name         example.com
state            valid
presented        True
age              15m
```

**Examples:**

```bash
# Get challenge details
ops k8s certs challenge get example-com-tls-1234567890-0

# Get in production namespace
ops k8s certs challenge get example-com-tls-1234567890-0 -n production

# Get full YAML definition
ops k8s certs challenge get example-com-tls-1234567890-0 -o yaml
```

---

#### `ops k8s certs challenge troubleshoot`

Troubleshoot an ACME Challenge with detailed diagnostic information.

```bash
ops k8s certs challenge troubleshoot <name> [OPTIONS]
```

**Arguments:**

| Argument | Required | Description             |
| -------- | -------- | ----------------------- |
| `name`   | Yes      | Challenge resource name |

**Options:**

| Option        | Short | Type   | Default   | Description                         |
| ------------- | ----- | ------ | --------- | ----------------------------------- |
| `--namespace` | `-n`  | string | `default` | Kubernetes namespace                |
| `--output`    | `-o`  | string | `table`   | Output format: table, json, or yaml |

**Example Output:**

```text
Challenge Troubleshooting: example-com-tls-1234567890-0

state                 valid
presented             True
error_message         None
wildcard              False
key                   [challenge-token-value]
token                 [acme-token-value]
authorizations_url    https://acme-v02.api.letsencrypt.org/acme/authz/...
solver_config:
  ingressClass: nginx
related_resources:
  - type: Ingress
    name: example-ingress
    namespace: production
```

**Examples:**

```bash
# Troubleshoot challenge
ops k8s certs challenge troubleshoot example-com-tls-1234567890-0

# Troubleshoot in specific namespace
ops k8s certs challenge troubleshoot example-com-tls-1234567890-0 -n cert-manager

# Get troubleshooting info as JSON
ops k8s certs challenge troubleshoot example-com-tls-1234567890-0 -o json
```

---

## Integration Examples

### Example 1: Create Certificates with Let's Encrypt (Production)

Set up production HTTPS using Let's Encrypt:

```bash
# Create ACME issuer for Let's Encrypt production
ops k8s certs acme create-issuer letsencrypt-prod \
  --email admin@example.com \
  --production \
  --ingress-class nginx \
  -n production

# Create certificate for your domain
ops k8s certs cert create example-com-tls \
  --secret-name example-com-cert \
  --issuer-name letsencrypt-prod \
  --dns-name example.com \
  --dns-name www.example.com \
  -n production

# Verify certificate status
ops k8s certs cert status example-com-tls -n production
```

### Example 2: Set Up Cluster-Wide Certificate Authority

Create a self-signed or internal CA for the entire cluster:

```bash
# Create self-signed cluster issuer
ops k8s certs clusterissuer create self-signed \
  --type selfSigned \
  --config '{}'

# Create CA cluster issuer (requires existing CA secret)
ops k8s certs clusterissuer create internal-ca \
  --type ca \
  --config '{"secretName":"internal-ca-pair"}' \
  --label scope=cluster-wide

# Create certificates using cluster issuer
ops k8s certs cert create api-internal-cert \
  --secret-name api-internal-tls \
  --issuer-name internal-ca \
  --issuer-kind ClusterIssuer \
  --dns-name api.internal.example.com
```

### Example 3: Monitor Certificate Expiry and Renewal

Track certificate lifecycle and force renewal when needed:

```bash
#!/bin/bash

# Check all certificates in namespace
ops k8s certs cert list -n production

# Get detailed status for specific certificate
STATUS=$(ops k8s certs cert status example-com-tls -n production -o json)

# Force renewal if approaching expiry
DAYS_REMAINING=$(echo "$STATUS" | grep -o '"daysRemaining":[0-9]*' | cut -d':' -f2)
if [ "$DAYS_REMAINING" -lt 30 ]; then
  ops k8s certs cert renew example-com-tls -n production
fi
```

### Example 4: Troubleshoot ACME Challenge Failures

Debug certificate issuance problems:

```bash
# List challenges in namespace
ops k8s certs challenge list -n production

# Get details of failing challenge
ops k8s certs challenge get example-com-tls-1234567890-0 -n production -o yaml

# Troubleshoot with diagnostic information
ops k8s certs challenge troubleshoot example-com-tls-1234567890-0 -n production

# Check certificate request status
ops k8s certs request get example-com-tls-1234567890 -n production -o yaml
```

### Example 5: Automate Certificate Creation for Microservices

Bulk create certificates for multiple services:

```bash
#!/bin/bash

NAMESPACE="production"
ISSUER="letsencrypt-prod"

# Create certificates for multiple domains
SERVICES=("api" "web" "admin" "docs")

for service in "${SERVICES[@]}"; do
  ops k8s certs cert create "$service-cert" \
    --secret-name "$service-tls" \
    --issuer-name "$ISSUER" \
    --dns-name "$service.example.com" \
    --label app="$service" \
    -n "$NAMESPACE"
done

# List all created certificates
ops k8s certs cert list -n "$NAMESPACE"
```

---

## Troubleshooting

| Issue                                   | Solution                                                             |
| --------------------------------------- | -------------------------------------------------------------------- |
| "Certificate CRD not found"             | cert-manager not installed. Install with: `kubectl apply -f          |
| Certificate stuck in "Not Ready" state  | Check CertificateRequest with `ops k8s                               |
| ACME challenges failing                 | Use `ops k8s certs challenge                                         |
| Let's Encrypt rate limits               | Switch to staging server for                                         |
| Permission denied creating certificates | Check RBAC with                                                      |
| Certificate renewal not happening       | Check `--renew-before` value is set correctly. Monitor with `ops k8s |
| Secret not created for certificate      | Verify the Secret resource specified in                              |
| Issuer shows "Not Ready"                | Check Issuer configuration and                                       |
| Cannot create ClusterIssuer             | ClusterIssuers are                                                   |

---

## See Also

- [cert-manager Official Documentation](https://cert-manager.io/)
- [Kubernetes Plugin Overview](../index.md)
- [Let's Encrypt](https://letsencrypt.org/)
- [ACME Protocol](https://tools.ietf.org/html/rfc8555)
- [Kubernetes Plugin Commands Reference](../commands/)
- [cert-manager Issuers](https://cert-manager.io/docs/concepts/issuer/)
- [cert-manager Certificates](https://cert-manager.io/docs/concepts/certificate/)
