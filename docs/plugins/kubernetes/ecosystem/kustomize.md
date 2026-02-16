# Kubernetes Plugin > Ecosystem > Kustomize

[< Back to Index](../index.md) | [Commands](../commands/) | [Ecosystem](./) | [TUI](../tui.md) | [Examples](../examples.md)

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Detection](#detection)
- [Configuration](#configuration)
- [Command Reference](#command-reference)
  - [build](#ops-k8s-kustomize-build)
  - [apply](#ops-k8s-kustomize-apply)
  - [diff](#ops-k8s-kustomize-diff)
  - [overlays](#ops-k8s-kustomize-overlays)
  - [validate](#ops-k8s-kustomize-validate)
- [Integration Examples](#integration-examples)
- [Troubleshooting](#troubleshooting)
- [See Also](#see-also)

---

## Overview

Kustomize is a template-free customization tool for Kubernetes manifests. It allows you to:

- **Compose Manifests**: Use base configurations with overlays for different environments
- **Apply Transformations**: Patch resources, rename, inject configuration without templating
- **Manage Complexity**: Keep DRY manifests with inheritance and patching
- **Support GitOps**: Version control your infrastructure with declarative, file-based configuration

The System Control CLI's Kustomize ecosystem tool provides comprehensive commands for:

- **Build Operations**: Render final manifests from base and overlay structures
- **Cluster Application**: Build and apply manifests directly to Kubernetes
- **Diff Analysis**: Compare Kustomize output against live cluster state
- **Overlay Discovery**: List and explore available overlays in your directories
- **Validation**: Verify Kustomization structure before deployment

### Why Use Kustomize with System Control

- **No Templating Language**: Pure YAML without Jinja, Helm, or Go templates
- **Environment Variations**: Easily maintain dev, staging, and production configurations
- **Strategic Merge Patches**: Surgically update only the fields you need to change
- **Resource Generators**: Create ConfigMaps and Secrets from files and variables
- **Multi-base Support**: Combine multiple bases for complex scenarios
- **GitOps Ready**: Perfect for declarative, version-controlled deployments

---

## Prerequisites

### Required

- **Kustomize Binary**: kubectl built-in kustomize (kubectl version 1.14+) or standalone kustomize binary
- **Kubernetes Access**: Valid kubeconfig and cluster connectivity via the core Kubernetes plugin
- **Permissions**: RBAC permissions to apply and view resources in target namespaces

### Optional

- **Helm Integration**: Enable `--enable-helm` for charts in your kustomization
- **Alpha Plugins**: Enable `--enable-alpha-plugins` for experimental Kustomize features
- **Directory Structure**: Standard base/overlays pattern for easy organization

### Installation

Kustomize is included with kubectl. For standalone kustomize:

```bash
# macOS with Homebrew
brew install kustomize

# Linux with curl
curl -s "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh" | bash
sudo mv kustomize /usr/local/bin/

# Verify installation
kustomize version
```

---

## Detection

The System Control CLI automatically detects Kustomize availability by:

1. Checking if `kustomize` binary exists in your PATH
2. Verifying binary functionality with basic commands
3. Testing compatibility with your Kubernetes cluster version

If Kustomize is not detected, you will see a clear error message:

```text
Error: Kustomize binary not found
Install kustomize: https://kubectl.docs.kubernetes.io/installation/kustomize/
```

---

## Configuration

Kustomize configuration is managed through your System Control CLI config files. No additional setup is required beyond
having the Kustomize binary installed.

### Environment Variables

Configure Kustomize behavior using standard environment variables:

```bash
# Set kubeconfig location
export KUBECONFIG=~/.kube/config

# Set default namespace for apply operations
export KUSTOMIZE_NAMESPACE=default

# Enable verbose output
export KUSTOMIZE_DEBUG=true
```

### Directory Structure

Follow the standard Kustomize directory layout:

```text
k8s/
├── base/
│   ├── kustomization.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   └── configmap.yaml
├── overlays/
│   ├── dev/
│   │   └── kustomization.yaml
│   ├── staging/
│   │   └── kustomization.yaml
│   └── prod/
│       └── kustomization.yaml
└── patches/
    ├── replicas.yaml
    ├── resources.yaml
    └── environment.yaml
```

---

## Command Reference

### `ops k8s kustomize build`

Build kustomization and render final manifests without applying to cluster.

```bash
ops k8s kustomize build PATH [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                                       |
| -------- | -------- | ------------------------------------------------- |
| `PATH`   | Yes      | Path to directory containing `kustomization.yaml` |

**Options:**

| Option                   | Short | Type | Default | Description                                   |
| ------------------------ | ----- | ---- | ------- | --------------------------------------------- |
| `--enable-helm`          | -     | flag | false   | Enable Helm chart inflation generator         |
| `--enable-alpha-plugins` | -     | flag | false   | Enable alpha Kustomize plugins                |
| `--output-file`          | `-f`  | path | -       | Write rendered YAML to file instead of stdout |

**Examples:**

```bash
# Build base configuration
ops k8s kustomize build ./k8s/base

# Build development overlay
ops k8s kustomize build ./overlays/dev

# Build and save to file
ops k8s kustomize build ./overlays/prod --output-file rendered-prod.yaml

# Build with Helm support
ops k8s kustomize build ./overlays/prod --enable-helm

# Build with alpha plugins
ops k8s kustomize build ./overlays/dev --enable-alpha-plugins
```

**Example Output:**

```yaml
---
apiVersion: v1
kind: Namespace
metadata:
  name: default
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config-abc123
  namespace: default
data:
  environment: production
  log_level: info
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: default
  labels:
    app: my-app
    version: v1.2.3
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
        version: v1.2.3
    spec:
      containers:
        - name: app
          image: myapp:v1.2.3
          ports:
            - containerPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: my-app
  namespace: default
spec:
  type: ClusterIP
  selector:
    app: my-app
  ports:
    - port: 80
      targetPort: 8080
```

---

### `ops k8s kustomize apply`

Build kustomization and apply rendered manifests to the cluster.

```bash
ops k8s kustomize apply PATH [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                                       |
| -------- | -------- | ------------------------------------------------- |
| `PATH`   | Yes      | Path to directory containing `kustomization.yaml` |

**Options:**

| Option             | Short | Type   | Default | Description                                |
| ------------------ | ----- | ------ | ------- | ------------------------------------------ |
| `--namespace`      | `-n`  | string | default | Kubernetes namespace for application       |
| `--dry-run`        | -     | flag   | false   | Client-side preview without server changes |
| `--server-dry-run` | -     | flag   | false   | Server-side dry run (validates on server)  |
| `--force`          | `-f`  | flag   | false   | Skip confirmation prompts                  |
| `--enable-helm`    | -     | flag   | false   | Enable Helm chart inflation generator      |
| `--output`         | `-o`  | string | table   | Output format: table, json, or yaml        |

**Examples:**

```bash
# Apply development overlay
ops k8s kustomize apply ./overlays/dev

# Apply to specific namespace
ops k8s kustomize apply ./overlays/prod -n production

# Preview changes before applying
ops k8s kustomize apply ./overlays/dev --dry-run

# Server-side validation
ops k8s kustomize apply ./overlays/dev --server-dry-run

# Apply with automatic confirmation
ops k8s kustomize apply ./overlays/prod -f

# Apply with Helm support
ops k8s kustomize apply ./overlays/prod --enable-helm
```

**Example Output:**

```text
Apply Results

RESOURCE                              NAMESPACE    ACTION       STATUS    MESSAGE
default/configmap/app-config-abc123   default      created      OK        Created successfully
default/service/my-app                default      created      OK        Created successfully
default/deployment/my-app             default      created      OK        Created successfully

Total: 3 resource(s)
```

---

### `ops k8s kustomize diff`

Build kustomization and show differences compared to live cluster state.

```bash
ops k8s kustomize diff PATH [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                                       |
| -------- | -------- | ------------------------------------------------- |
| `PATH`   | Yes      | Path to directory containing `kustomization.yaml` |

**Options:**

| Option          | Short | Type   | Default | Description                           |
| --------------- | ----- | ------ | ------- | ------------------------------------- |
| `--namespace`   | `-n`  | string | default | Kubernetes namespace                  |
| `--enable-helm` | -     | flag   | false   | Enable Helm chart inflation generator |
| `--output`      | `-o`  | string | table   | Output format: table, json, or yaml   |

**Examples:**

```bash
# Compare overlay against cluster
ops k8s kustomize diff ./overlays/dev

# Compare in specific namespace
ops k8s kustomize diff ./overlays/prod -n production

# Compare with Helm support
ops k8s kustomize diff ./overlays/prod --enable-helm

# Output as JSON for scripting
ops k8s kustomize diff ./overlays/dev --output json
```

**Example Output:**

```text
Diff Summary

RESOURCE                          NAMESPACE    ON CLUSTER    STATUS
configmap/app-config-abc123       default      Yes           Changed
service/my-app                    default      No            New
deployment/my-app                 default      Yes           Changed

configmap/app-config-abc123:
---
metadata:
  labels:
    app: my-app
data:
  environment: development
+ log_level: debug

deployment/my-app:
---
spec:
  replicas: 1
- replicas: 2
+ containers[0].image: myapp:v1.2.4
- image: myapp:v1.2.3

service/my-app:
+++ New resource
+apiVersion: v1
+kind: Service
+metadata:
+  name: my-app
+spec:
+  type: ClusterIP
+  selector:
+    app: my-app
```

---

### `ops k8s kustomize overlays`

List available overlays in a directory tree.

```bash
ops k8s kustomize overlays PATH [OPTIONS]
```

**Arguments:**

| Argument | Required | Description                                     |
| -------- | -------- | ----------------------------------------------- |
| `PATH`   | Yes      | Path to directory containing overlays structure |

**Options:**

| Option     | Short | Type   | Default | Description                         |
| ---------- | ----- | ------ | ------- | ----------------------------------- |
| `--output` | `-o`  | string | table   | Output format: table, json, or yaml |

**Examples:**

```bash
# List overlays in current directory
ops k8s kustomize overlays .

# List overlays in k8s directory
ops k8s kustomize overlays ./k8s

# Output as JSON
ops k8s kustomize overlays ./k8s --output json

# Save overlay list for documentation
ops k8s kustomize overlays ./overlays --output json > overlays.json
```

**Example Output:**

```text
Kustomize Overlays

NAME       PATH                      VALID    RESOURCES
base       ./base                    Yes      5 resource(s)
dev        ./overlays/dev            Yes      5 resource(s)
staging    ./overlays/staging        Yes      5 resource(s)
prod       ./overlays/prod           Yes      6 resource(s)

Total: 4 overlay(s)
```

---

### `ops k8s kustomize validate`

Validate a kustomization directory structure.

```bash
ops k8s kustomize validate PATH
```

**Arguments:**

| Argument | Required | Description                                       |
| -------- | -------- | ------------------------------------------------- |
| `PATH`   | Yes      | Path to directory containing `kustomization.yaml` |

**Examples:**

```bash
# Validate base configuration
ops k8s kustomize validate ./k8s/base

# Validate development overlay
ops k8s kustomize validate ./overlays/dev

# Validate production overlay
ops k8s kustomize validate ./overlays/prod
```

**Example Output (Success):**

```text
Kustomization valid: ./overlays/dev
```

**Example Output (Failure):**

```text
Kustomization invalid: ./overlays/dev
  Error: kustomization.yaml not found in ./overlays/dev
```

---

## Integration Examples

### Example 1: Basic Base and Overlay Structure

Create and manage a simple application with base and overlay configurations:

```bash
# Create directory structure
mkdir -p k8s/{base,overlays/{dev,staging,prod}}

# Create base kustomization.yaml
cat > k8s/base/kustomization.yaml << 'EOF'
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: default

commonLabels:
  app: myapp

resources:
  - deployment.yaml
  - service.yaml

configMapGenerator:
  - name: app-config
    literals:
      - LOG_LEVEL=info
EOF

# Create base resources
cat > k8s/base/deployment.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 2
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: app
        image: myapp:v1.0.0
        ports:
        - containerPort: 8080
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
EOF

# Create development overlay
cat > k8s/overlays/dev/kustomization.yaml << 'EOF'
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

bases:
  - ../../base

namespace: development

namePrefix: dev-

replicas:
  - name: myapp
    count: 1

configMapGenerator:
  - name: app-config
    literals:
      - LOG_LEVEL=debug

patchesStrategicMerge:
  - deployment-patch.yaml
EOF

# Deploy to environments
ops k8s kustomize apply ./k8s/overlays/dev -n development
ops k8s kustomize apply ./k8s/overlays/staging -n staging
ops k8s kustomize apply ./k8s/overlays/prod -n production
```

### Example 2: Multi-environment with Resource Limits

Deploy the same application with different resource configurations:

```bash
# Create production overlay with resource limits
cat > k8s/overlays/prod/kustomization.yaml << 'EOF'
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

bases:
  - ../../base

namespace: production

namePrefix: prod-

replicas:
  - name: myapp
    count: 3

configMapGenerator:
  - name: app-config
    literals:
      - LOG_LEVEL=error
      - ENVIRONMENT=production

patchesStrategicMerge:
  - deployment-patch.yaml
EOF

cat > k8s/overlays/prod/deployment-patch.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    spec:
      containers:
      - name: app
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 1Gi
EOF

# Preview what will be deployed
ops k8s kustomize build ./k8s/overlays/prod

# Apply to production
ops k8s kustomize apply ./k8s/overlays/prod -n production --dry-run
ops k8s kustomize apply ./k8s/overlays/prod -n production
```

### Example 3: Patching and Customization

Use patches to customize resources without duplicating entire manifests:

```bash
# Create patch files for different environments
cat > k8s/overlays/staging/replica-patch.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 2
EOF

cat > k8s/overlays/staging/image-patch.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    spec:
      containers:
      - name: app
        image: myapp:staging-latest
EOF

cat > k8s/overlays/staging/kustomization.yaml << 'EOF'
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

bases:
  - ../../base

namespace: staging

patchesStrategicMerge:
  - replica-patch.yaml
  - image-patch.yaml

configMapGenerator:
  - name: app-config
    literals:
      - LOG_LEVEL=info
      - ENVIRONMENT=staging
EOF

# Validate patches
ops k8s kustomize validate ./k8s/overlays/staging

# Review changes
ops k8s kustomize diff ./k8s/overlays/staging -n staging

# Apply changes
ops k8s kustomize apply ./k8s/overlays/staging -n staging
```

### Example 4: Discovery and Validation Workflow

Discover and validate overlays before deployment:

```bash
# List all available overlays
ops k8s kustomize overlays ./k8s

# Validate each overlay
ops k8s kustomize validate ./k8s/base
ops k8s kustomize validate ./k8s/overlays/dev
ops k8s kustomize validate ./k8s/overlays/staging
ops k8s kustomize validate ./k8s/overlays/prod

# Build and save all configurations
for overlay in base dev staging prod; do
  ops k8s kustomize build ./k8s/overlays/$overlay \
    --output-file ./rendered/$overlay.yaml
done

# Review rendered files
ls -lah ./rendered/
cat ./rendered/prod.yaml | head -50
```

### Example 5: GitOps Workflow with Kustomize

Integrate Kustomize into a GitOps workflow:

```bash
# Clone manifests repository
git clone https://github.com/company/k8s-manifests
cd k8s-manifests

# Create feature branch
git checkout -b feature/update-image

# Make changes
cat > k8s/overlays/prod/image-patch.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    spec:
      containers:
      - name: app
        image: myapp:v1.2.3
EOF

# Preview changes
ops k8s kustomize diff ./k8s/overlays/prod -n production

# Commit and push
git add k8s/
git commit -m "feat: update image to v1.2.3"
git push origin feature/update-image

# After PR approval, pull and deploy
git checkout main
git pull
ops k8s kustomize apply ./k8s/overlays/prod -n production
```

---

## Troubleshooting

| Issue                                | Solution                                         |
| ------------------------------------ | ------------------------------------------------ |
| **Kustomize binary not found**       | Install standalone kustomize following [official |
| **kustomization.yaml not found**     | Ensure directory contains                        |
| **Build fails with patch error**     | Verify patch targets                             |
| **ConfigMap hash mismatch**          | ConfigMaps regenerate hashes when                |
| **Namespace not found**              | Create namespace                                 |
| **Resources already exist**          | Delete and reapply:                              |
| **Helm integration not working**     | Ensure `--enable-hel                             |
| **Image tag changes not reflected**  | Kustomize doesn't                                |
| **Apply hangs or times out**         | Check cluster connectivity: `kubectl             |
| **Secret or ConfigMap regeneration** | Use `immutable: true` in kustomization.ya        |
| **Permission denied errors**         | Check RBAC: `kubectl                             |
| **Overlays not discoverable**        | Ensure kustomization                             |
| **Diff shows unexpected changes**    | Run `ops k8s kustomize                           |
| **Alpha plugins not recognized**     | Use `--enable-alpha-                             |

---

## See Also

- [Kustomize Official Documentation](https://kustomize.io/)
- [Kubernetes Kustomize Reference](https://kubectl.docs.kubernetes.io/references/kustomize/)
- [Kubernetes Plugin Index](../index.md)
- [Helm Ecosystem](./helm.md)
- [ArgoCD Ecosystem](./argocd.md)
- [Kubernetes Commands Reference](../commands/)
- [Kubernetes Integration Guide](../../integrations/kubernetes.md)
