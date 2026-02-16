# Kubernetes Plugin > Examples

[< Back to Index](./index.md) | [Commands](./commands/) | [Ecosystem](./ecosystem/) | [TUI](./tui.md) | [Troubleshooting](./troubleshooting.md)

Comprehensive examples for managing Kubernetes clusters with the ops CLI. Each section includes
context, prerequisites, step-by-step commands, expected output, and troubleshooting tips.

---

## Table of Contents

- [Getting Started with Your First Cluster](#getting-started-with-your-first-cluster)
- [Multi-Cluster Setup and Switching](#multi-cluster-setup-and-switching)
- [Authentication Methods](#authentication-methods)
- [Deploying a Microservice](#deploying-a-microservice)
- [Helm Chart Lifecycle](#helm-chart-lifecycle)
- [GitOps with ArgoCD](#gitops-with-argocd)
- [Progressive Delivery with Argo Rollouts](#progressive-delivery-with-argo-rollouts)
- [Certificate Management](#certificate-management)
- [Policy Enforcement with Kyverno](#policy-enforcement-with-kyverno)
- [TUI Walkthrough](#tui-walkthrough)
- [Resource Optimization](#resource-optimization)
- [Manifest Management](#manifest-management)

---

## Getting Started with Your First Cluster

### Connecting to Your First Cluster

**Context**: Before running any Kubernetes commands, verify that the CLI can connect to your
Kubernetes cluster and explore what's available.

**Prerequisites**:

- Kubernetes cluster running and accessible
- Valid kubeconfig file at `~/.kube/config`
- `kubectl` binary available on your system

**Step 1: Check Cluster Status**

Verify connectivity to your Kubernetes cluster:

```bash
ops k8s status
```

**Expected Output**:

```text
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Property        ┃ Value    ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ Context         │ minikube │
│ Namespace       │ default  │
│ Connected       │ Yes      │
│ Cluster Version │ v1.27.4  │
│ Nodes           │ 1        │
└─────────────────┴──────────┘
```

**Step 2: List Available Contexts**

See all Kubernetes contexts configured on your system:

```bash
ops k8s contexts
```

**Expected Output**:

```text
┏━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃   ┃ Name     ┃ Cluster            ┃ Namespace ┃
┡━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ * │ minikube │ minikube           │ default   │
│   │ docker   │ docker-for-desktop │ default   │
└───┴──────────┴────────────────────┴───────────┘
```

**Step 3: View Cluster Information**

Get detailed cluster information:

```bash
ops k8s cluster-info
```

**Expected Output**:

```text
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property    ┃ Value                   ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ api_server  │ https://127.0.0.1:32768 │
│ version     │ v1.27.4                 │
│ platform    │ linux/amd64             │
│ git_version │ v1.27.4                 │
│ build_date  │ 2023-08-16T12:34:56Z    │
└─────────────┴─────────────────────────┘
```

**Step 4: List Nodes**

See the nodes in your cluster:

```bash
ops k8s nodes list
```

**Expected Output**:

```text
┏━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━┓
┃ Name     ┃ Status ┃ Roles         ┃ Version ┃ Internal-IP  ┃ Age ┃
┡━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━┩
│ minikube │ Ready  │ control-plane │ v1.27.4 │ 192.168.1.10 │ 30d │
└──────────┴────────┴───────────────┴─────────┴──────────────┴─────┘
```

**Troubleshooting**:

| Issue                 | Solution                                                                                  |
| --------------------- | ----------------------------------------------------------------------------------------- |
| Connection refused    | Verify cluster is running: `minikube status` or equivalent for your                       |
| Timeout               | Check network connectivity to cluster API server. Verify firewall rules allow connections |
| Authentication failed | Verify kubeconfig credentials with `kubectl                                               |

---

## Multi-Cluster Setup and Switching

### Configuring Three Clusters (Dev/Staging/Production)

**Context**: Manage multiple Kubernetes clusters (development, staging, production) from a single
CLI with easy switching and verification.

**Prerequisites**:

- Three Kubernetes clusters accessible and running
- Valid kubeconfig files or contexts for each cluster
- Network connectivity to all clusters

**Step 1: Create Configuration File**

Set up your ops config with three clusters:

```bash
mkdir -p ~/.config/ops
cat > ~/.config/ops/config.yaml << 'EOF'
plugins:
  kubernetes:
    clusters:
      dev:
        context: "docker-desktop"
        kubeconfig: "~/.kube/config"
        namespace: "development"
        timeout: 300

      staging:
        context: "staging-cluster"
        kubeconfig: "~/.kube/staging.yaml"
        namespace: "staging"
        timeout: 300

      production:
        context: "prod-cluster"
        kubeconfig: "~/.kube/production.yaml"
        namespace: "default"
        timeout: 600

    active_cluster: "dev"

    defaults:
      timeout: 300
      retry_attempts: 3
      dry_run_strategy: "none"

    auth:
      type: "kubeconfig"
EOF
```

**Step 2: Verify Current Cluster**

Check which cluster is active:

```bash
ops k8s status
```

**Expected Output**:

```text
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ Property        ┃ Value          ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ Context         │ docker-desktop │
│ Namespace       │ development    │
│ Connected       │ Yes            │
│ Cluster Version │ v1.25.0        │
│ Nodes           │ 1              │
└─────────────────┴────────────────┘
```

**Step 3: Switch to Staging**

Switch to the staging cluster:

```bash
ops k8s use-context staging-cluster
ops k8s status
```

**Expected Output**:

```text
Switched to context 'staging-cluster'

┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
┃ Property        ┃ Value           ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━┩
│ Context         │ staging-cluster │
│ Namespace       │ staging         │
│ Connected       │ Yes             │
│ Cluster Version │ v1.27.2         │
│ Nodes           │ 3               │
└─────────────────┴─────────────────┘
```

**Step 4: Switch to Production**

Switch to the production cluster:

```bash
ops k8s use-context prod-cluster
ops k8s status
```

**Expected Output**:

```text
Switched to context 'prod-cluster'

┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Property        ┃ Value        ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ Context         │ prod-cluster │
│ Namespace       │ default      │
│ Connected       │ Yes          │
│ Cluster Version │ v1.27.4      │
│ Nodes           │ 5            │
└─────────────────┴──────────────┘
```

**Step 5: Override Context for Single Command**

Execute a command against a specific cluster without changing context:

```bash
OPS_K8S_CONTEXT=staging-cluster ops k8s pods list -n staging
```

**Expected Output**:

```text
┏━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┳━━━━━┓
┃ Name         ┃ Ready ┃ Status  ┃ Restarts ┃ Age ┃
┡━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━╇━━━━━┩
│ api-server-1 │ 1/1   │ Running │ 0        │ 10d │
│ api-server-2 │ 1/1   │ Running │ 0        │ 10d │
└──────────────┴───────┴─────────┴──────────┴─────┘
```

**Troubleshooting**:

| Issue                         | Solution                                                                          |
| ----------------------------- | --------------------------------------------------------------------------------- |
| Context not found             | Check kubeconfig file exists at specified path. Run `kubectl config get-contexts` |
| Different kubeconfig paths    | Ensure each cluster definition has correct kubeconfig                             |
| Switching doesn't take effect | Environment variable OPS_K8S_CONTEXT overrides                                    |

---

## Authentication Methods

### Kubeconfig Authentication (Default)

**Context**: Using the standard kubeconfig file authentication method, which is the default and
most common approach.

```bash
# Configure kubeconfig auth
cat > ~/.config/ops/config.yaml << 'EOF'
plugins:
  kubernetes:
    auth:
      type: "kubeconfig"
    clusters:
      dev:
        kubeconfig: "~/.kube/config"
        context: "minikube"
        namespace: "default"
EOF

# Verify authentication works
ops k8s status
```

### Token-Based Authentication

**Context**: Using a bearer token for authentication, common in CI/CD pipelines and automation.

```bash
# Store token in environment variable
export OPS_K8S_TOKEN="<your-bearer-token>"

# Or configure in ops config
cat > ~/.config/ops/config.yaml << 'EOF'
plugins:
  kubernetes:
    auth:
      type: "token"
      token: "${OPS_K8S_TOKEN}"
    clusters:
      prod:
        context: "prod-cluster"
        namespace: "default"
        kubeconfig: "~/.kube/config"  # Still need kubeconfig for server info
EOF

# Test token authentication
ops k8s pods list
```

### Service Account Authentication

**Context**: When running commands from within a Kubernetes pod, using mounted service account.

```bash
# Configure in-cluster service account auth
cat > /etc/ops/config.yaml << 'EOF'
plugins:
  kubernetes:
    auth:
      type: "service_account"
      token_path: "/var/run/secrets/kubernetes.io/serviceaccount/token"
      ca_path: "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
    clusters:
      local:
        context: "local"
        namespace: "default"
EOF

# Use from within pod
ops k8s pods list
```

### Certificate-Based Authentication

**Context**: Using client certificates (mTLS) for authentication.

```bash
# Configure certificate-based auth
cat > ~/.config/ops/config.yaml << 'EOF'
plugins:
  kubernetes:
    auth:
      type: "certificate"
      cert_path: "/etc/kubernetes/pki/client.crt"
      key_path: "/etc/kubernetes/pki/client.key"
      ca_path: "/etc/kubernetes/pki/ca.crt"
    clusters:
      prod:
        context: "prod-cluster"
        namespace: "default"
EOF

# Test certificate authentication
ops k8s status
```

---

## Deploying a Microservice

### Complete Microservice Deployment Workflow

**Context**: Deploy a complete microservice application with namespace, deployment, service,
and verify the deployment works correctly.

**Prerequisites**:

- Kubernetes cluster running with kubectl access
- Container image available (using public nginx for this example)

**Step 1: Create Namespace**

Create a dedicated namespace for your application:

```bash
ops k8s namespaces create my-app -l env=production -l team=backend
```

**Expected Output**:

```text
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
┃ Property ┃ Value           ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━━┩
│ Name     │ my-app          │
│ Status   │ Active          │
│ Age      │ 0s              │
│ Labels   │ env: production │
│          │ team: backend   │
└──────────┴─────────────────┘
```

**Step 2: Create ConfigMap for Configuration**

Store application configuration:

```bash
ops k8s configmaps create app-config \
  -n my-app \
  --data "log_level=info" \
  --data "database_url=postgres://db:5432/myapp" \
  --data "cache_enabled=true"
```

**Expected Output**:

```text
ConfigMap 'app-config' created in namespace 'my-app'
```

**Step 3: Create Secret for Credentials**

Store sensitive data:

```bash
ops k8s secrets create app-credentials \
  -n my-app \
  --data "db_username=admin" \
  --data "db_password=secret123" \
  --data "api_key=<your-api-key>"
```

**Expected Output**:

```text
Secret 'app-credentials' created in namespace 'my-app'
```

**Step 4: Create Deployment**

Create a deployment manifest and apply it:

```bash
cat > deployment.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: my-app
  labels:
    app: my-app
    version: v1
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 1
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
        version: v1
    spec:
      containers:
      - name: app
        image: nginx:latest
        ports:
        - containerPort: 80
          name: http
        env:
        - name: LOG_LEVEL
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: log_level
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: app-credentials
              key: db_password
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
        livenessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 5
EOF

ops k8s manifest apply -f deployment.yaml
```

**Expected Output**:

```text
deployment.apps/my-app created
```

**Step 5: Verify Deployment Status**

Check the deployment and pods:

```bash
ops k8s deployments get my-app -n my-app
```

**Expected Output**:

```text
┏━━━━━━━━━━━┳━━━━━━━━┓
┃ Property  ┃ Value  ┃
┡━━━━━━━━━━━╇━━━━━━━━┩
│ Name      │ my-app │
│ Replicas  │ 3/3    │
│ Ready     │ 3/3    │
│ Updated   │ 3/3    │
│ Available │ 3/3    │
│ Age       │ 2m     │
└───────────┴────────┘
```

**Step 6: Verify Pods Are Running**

List pods in the deployment:

```bash
ops k8s pods list -n my-app
```

**Expected Output**:

```text
┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┳━━━━━┓
┃ Name                   ┃ Ready ┃ Status  ┃ Restarts ┃ Age ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━╇━━━━━┩
│ my-app-7d8c5b9f4-abc1d │ 1/1   │ Running │ 0        │ 2m  │
│ my-app-7d8c5b9f4-def2e │ 1/1   │ Running │ 0        │ 2m  │
│ my-app-7d8c5b9f4-ghi3f │ 1/1   │ Running │ 0        │ 2m  │
└────────────────────────┴───────┴─────────┴──────────┴─────┘
```

**Step 7: Create Service**

Expose the deployment with a service:

```bash
cat > service.yaml << 'EOF'
apiVersion: v1
kind: Service
metadata:
  name: my-app
  namespace: my-app
  labels:
    app: my-app
spec:
  type: ClusterIP
  ports:
  - port: 80
    targetPort: 80
    protocol: TCP
    name: http
  selector:
    app: my-app
EOF

ops k8s manifest apply -f service.yaml
```

**Expected Output**:

```text
service/my-app created
```

**Step 8: View Service Details**

Check the service and its endpoints:

```bash
ops k8s services get my-app -n my-app
```

**Expected Output**:

```text
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Property    ┃ Value      ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ Name        │ my-app     │
│ Type        │ ClusterIP  │
│ Cluster IP  │ 10.0.0.100 │
│ Port        │ 80         │
│ Target Port │ 80         │
│ Endpoints   │ 3 active   │
│ Age         │ 1m         │
└─────────────┴────────────┘
```

**Step 9: Scale the Deployment**

Increase the number of replicas:

```bash
ops k8s deployments scale my-app -n my-app --replicas 5
```

**Expected Output**:

```text
Scaled deployment 'my-app' to 5 replicas
```

**Step 10: View Application Logs**

Check logs from a pod:

```bash
ops k8s logs my-app-7d8c5b9f4-abc1d -n my-app
```

**Expected Output**:

```text
/docker-entrypoint.sh: /docker-entrypoint.d/ is not empty, will attempt to start nginx
/docker-entrypoint.sh: Looking for shell scripts in /docker-entrypoint.d/
/docker-entrypoint.sh: Launching /docker-entrypoint.d/10-listen-on-ipv6-by-default.sh
10-listen-on-ipv6-by-default.sh: info: Getting the checksum of /etc/nginx/conf.d/default.conf
nginx: [notice] signal process started
```

**Troubleshooting**:

| Issue                               | Solution                                                                 |
| ----------------------------------- | ------------------------------------------------------------------------ |
| Pod not starting (ImagePullBackOff) | Verify image name and repository access. Check image exists with `docker |
| CrashLoopBackOff                    | Check pod logs with `ops k8s logs <pod>`. Verify environment             |
| Service endpoint shows none         | Verify pod labels match service selector. Check pods are                 |

---

## Helm Chart Lifecycle

### Managing Helm Charts Complete Workflow

**Context**: Add a Helm repository, search for charts, install a release, upgrade with new values,
and manage the release lifecycle.

**Prerequisites**:

- Helm binary installed and in PATH
- Kubernetes cluster accessible
- Internet access to Helm repositories

**Step 1: Add Helm Repository**

Add a Helm repository:

```bash
ops k8s helm repo add stable https://charts.helm.sh/stable
ops k8s helm repo add bitnami https://charts.bitnami.com/bitnami
```

**Expected Output**:

```text
Repository 'stable' added successfully
Repository 'bitnami' added successfully
```

**Step 2: Search for Available Charts**

Search for a chart:

```bash
ops k8s helm search stable/mysql
ops k8s helm search bitnami/wordpress
```

**Expected Output**:

```text
NAME                    CHART VERSION   APP VERSION     DESCRIPTION
stable/mysql            1.6.9           5.7.30          Fast, reliable, scalable, and easy to use open...
stable/percona          1.2.3           5.7.26          A Helm chart for Percona
stable/percona-xtradb   1.0.2           5.7.26          A Helm chart for Percona
```

**Step 3: Create Namespace for Helm Release**

Create a namespace for the Helm release:

```bash
ops k8s namespaces create helm-apps -l app=helm
```

**Expected Output**:

```text
Namespace 'helm-apps' created
```

**Step 4: Install Helm Chart**

Install a Helm chart:

```bash
ops k8s helm install mysql-db stable/mysql \
  -n helm-apps \
  --set mysqlRootPassword=rootpassword123 \
  --set mysqlUser=appuser \
  --set mysqlPassword=userpassword123 \
  --set persistence.enabled=true \
  --set persistence.size=10Gi
```

**Expected Output**:

```text
Release 'mysql-db' installed successfully
CHART: stable/mysql
STATUS: deployed
REVISION: 1
NAMESPACE: helm-apps
```

**Step 5: Check Release Status**

View the status of a Helm release:

```bash
ops k8s helm status mysql-db -n helm-apps
```

**Expected Output**:

```text
NAME: mysql-db
NAMESPACE: helm-apps
STATUS: deployed
REVISION: 1
UPDATED: 2024-02-16T10:30:45Z
CHART: mysql-1.6.9
APP VERSION: 5.7.30

NOTES:
MySQL can be accessed via port 3306 on the following DNS name from within your cluster:
mysql-db.helm-apps.svc.cluster.local
```

**Step 6: List Helm Releases**

View all Helm releases:

```bash
ops k8s helm list -n helm-apps
```

**Expected Output**:

```text
NAME         NAMESPACE   REVISION   UPDATED                   STATUS    CHART
mysql-db     helm-apps   1          2024-02-16T10:30:45Z     deployed  mysql-1.6.9
```

**Step 7: Get Release Values**

View the current values used by a release:

```bash
ops k8s helm get-values mysql-db -n helm-apps
```

**Expected Output**:

```yaml
mysqlDatabase: myapp
mysqlPassword: userpassword123
mysqlRootPassword: rootpassword123
mysqlUser: appuser
persistence:
  enabled: true
  size: 10Gi
```

**Step 8: Upgrade Release with New Values**

Update the release with new configuration:

```bash
ops k8s helm upgrade mysql-db stable/mysql \
  -n helm-apps \
  --set persistence.size=20Gi \
  --set resources.limits.memory=1Gi \
  --set resources.requests.memory=512Mi
```

**Expected Output**:

```text
Release 'mysql-db' upgraded successfully
CHART: stable/mysql
STATUS: deployed
REVISION: 2
```

**Step 9: View Release History**

Check the release history:

```bash
ops k8s helm history mysql-db -n helm-apps
```

**Expected Output**:

```text
REVISION   UPDATED                   STATUS      CHART           APP VERSION   DESCRIPTION
1          2024-02-16T10:30:45Z     superseded  mysql-1.6.9     5.7.30        Install complete
2          2024-02-16T10:35:22Z     deployed    mysql-1.6.9     5.7.30        Upgrade complete
```

**Step 10: Rollback Release**

Rollback to a previous version:

```bash
ops k8s helm rollback mysql-db 1 -n helm-apps
```

**Expected Output**:

```text
Release 'mysql-db' rolled back to revision 1
CHART: mysql
STATUS: deployed
REVISION: 3
```

**Step 11: Uninstall Release**

Remove a Helm release:

```bash
ops k8s helm uninstall mysql-db -n helm-apps
```

**Expected Output**:

```text
Release 'mysql-db' uninstalled
```

**Troubleshooting**:

| Issue                                  | Solution                                                                |
| -------------------------------------- | ----------------------------------------------------------------------- |
| Chart not found                        | Verify repository is added with `ops k8s helm repo list`.               |
| Installation fails with invalid values | Validate chart values with `ops k8s helm template mysql-db              |
| Release stuck in pending               | Check pod status with `ops k8s pods list -n namespace`. View pod events |

---

## GitOps with ArgoCD

### Complete ArgoCD Application Lifecycle

**Context**: Create an ArgoCD application, sync application state, check status, and manage
projects for multi-application deployments.

**Prerequisites**:

- ArgoCD installed in the cluster (`argocd` namespace)
- Git repository with Kubernetes manifests
- kubectl access to the cluster

**Step 1: Create ArgoCD Application**

Create an application that monitors a Git repository:

```bash
ops k8s argocd applications create my-app \
  --repo https://github.com/example/manifests.git \
  --revision main \
  --path apps/my-app \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace my-app \
  --sync-policy auto
```

**Expected Output**:

```text
Application 'my-app' created
Name:           my-app
Project:        default
Sync Status:    OutOfSync
Health Status:  Unknown
Git Repo:       https://github.com/example/manifests.git
Git Revision:   main
Path:           apps/my-app
```

**Step 2: List ArgoCD Applications**

View all ArgoCD applications:

```bash
ops k8s argocd applications list
```

**Expected Output**:

```text
NAME         SYNC STATUS   HEALTH STATUS   PROJECT   NAMESPACE
my-app       OutOfSync     Unknown         default   my-app
auth-svc     Synced        Healthy         default   auth
api-gateway  Synced        Healthy         default   api
```

**Step 3: Get Application Details**

View detailed information about an application:

```bash
ops k8s argocd applications get my-app
```

**Expected Output**:

```text
Name:           my-app
Project:        default
Sync Status:    OutOfSync
Health Status:  Unknown
Sync Policy:    Automated
Git Repo:       https://github.com/example/manifests.git
Git Revision:   main
Path:           apps/my-app
Dest Server:    https://kubernetes.default.svc
Dest Namespace: my-app

Conditions:
  CONDITION             MESSAGE
  ComparisonFailed      Could not determine application health
```

**Step 4: Sync Application**

Synchronize the application to desired state:

```bash
ops k8s argocd applications sync my-app
```

**Expected Output**:

```text
SYNC RESULT:
Sync Status:   Synced
Synced At:     2024-02-16T10:45:30Z
Sync Duration: 30s

RESOURCES SYNCED:
NAME                      TYPE        STATUS
deployment-my-app         Deployment  synced
service-my-app            Service     synced
configmap-my-app          ConfigMap   synced
```

**Step 5: Check Application Health**

View application health status:

```bash
ops k8s argocd applications get my-app --output json | grep -A 5 health
```

**Expected Output**:

```json
{
  "health_status": "Healthy",
  "status": {
    "sync": {
      "status": "Synced",
      "compared_to": {
        "git": {
          "repo": "https://github.com/example/manifests.git",
          "path": "apps/my-app",
          "revision": "main"
        }
      }
    }
  }
}
```

**Step 6: Create ArgoCD Project**

Create a project for multi-application management:

```bash
ops k8s argocd projects create production \
  --description "Production environment applications" \
  --allowed-namespace production \
  --allowed-cluster https://kubernetes.default.svc
```

**Expected Output**:

```text
Project 'production' created
```

**Step 7: List Projects**

View all ArgoCD projects:

```bash
ops k8s argocd projects list
```

**Expected Output**:

```text
NAME          DESCRIPTION
default       default project
production    Production environment applications
staging       Staging environment applications
```

**Step 8: Update Application Project**

Move application to a different project:

```bash
ops k8s argocd applications update my-app --project production
```

**Expected Output**:

```text
Application 'my-app' updated
```

**Troubleshooting**:

| Issue                            | Solution                                                              |
| -------------------------------- | --------------------------------------------------------------------- |
| Application OutOfSync            | Run sync command: `ops k8s argocd applications sync <app>`. Check git |
| Sync fails with credential error | Verify Git credentials stored in ArgoCD. Update repository            |
| Health status Unknown            | Wait for application to finish syncing. Check pod                     |

---

## Progressive Delivery with Argo Rollouts

### Canary Deployment with Argo Rollouts

**Context**: Deploy a new version of an application using canary strategy with automatic
promotion and analysis.

**Prerequisites**:

- Argo Rollouts installed in cluster
- Current production deployment running
- New application version ready to deploy

**Step 1: List Current Rollouts**

View existing Argo Rollouts:

```bash
ops k8s rollouts list -n production
```

**Expected Output**:

```text
NAME              KIND          DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE
api-server        Rollout       3         3         3       3            3
web-frontend      Rollout       5         5         5       5            5
```

**Step 2: Get Rollout Details**

View detailed information about a rollout:

```bash
ops k8s rollouts get api-server -n production
```

**Expected Output**:

```text
Name:              api-server
Namespace:         production
Status:            Healthy
Strategy:          Canary
Desired Replicas:  3
Current Replicas:  3
Ready Replicas:    3

Canary:
  Weight:          0%
  Desired:         0
  Current:         0
```

**Step 3: Create Canary Rollout**

Create a rollout with canary strategy:

```bash
cat > rollout.yaml << 'EOF'
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: api-server-v2
  namespace: production
spec:
  replicas: 3
  strategy:
    canary:
      steps:
      - setCanaryScale:
          replicas: 1
      - pause:
          duration: 5m
      - setCanaryScale:
          replicas: 2
      - pause:
          duration: 5m
      - setCanaryScale:
          replicas: 3
      - pause:
          duration: 5m
      analysis:
        templates:
        - name: error-rate
          interval: 30s
          successCriteria:
            limit:
              value: 95
        startingStep: 0
  selector:
    matchLabels:
      app: api-server
  template:
    metadata:
      labels:
        app: api-server
    spec:
      containers:
      - name: api
        image: api-server:v2
        ports:
        - containerPort: 8080
EOF

ops k8s manifest apply -f rollout.yaml
```

**Step 4: Check Rollout Progress**

Monitor canary rollout progress:

```bash
ops k8s rollouts get api-server-v2 -n production
```

**Expected Output**:

```text
Name:              api-server-v2
Namespace:         production
Status:            Progressing
Strategy:          Canary
Desired Replicas:  3
Current Replicas:  2
Ready Replicas:    2

Canary:
  Weight:          50%
  Desired:         2
  Current:         2
  Step:            2/4
  Pause Until:     2024-02-16T11:05:30Z
```

**Step 5: Promote Canary to Next Step**

Manually promote the canary to the next step:

```bash
ops k8s rollouts promote api-server-v2 -n production
```

**Expected Output**:

```text
Rollout 'api-server-v2' promoted to next step
Current Step:  3/4
Canary Weight: 100%
```

**Step 6: Check Analysis Results**

View analysis results from the rollout:

```bash
ops k8s rollouts get api-server-v2 -n production --output json | grep -A 10 analysis
```

**Expected Output**:

```json
{
  "analysis": {
    "status": "Successful",
    "error_rate": {
      "current": "2.3%",
      "threshold": "5%"
    },
    "p99_latency": {
      "current": "145ms",
      "threshold": "200ms"
    }
  }
}
```

**Step 7: Complete Rollout**

Wait for rollout to complete or manually finalize:

```bash
ops k8s rollouts get api-server-v2 -n production
```

**Expected Output**:

```text
Name:              api-server-v2
Namespace:         production
Status:            Healthy
Strategy:          Canary
Desired Replicas:  3
Current Replicas:  3
Ready Replicas:    3

Canary:
  Weight:          100%
  Desired:         3
  Current:         3
  Step:            4/4
```

**Step 8: Rollback if Needed**

Abort rollout and rollback to previous version:

```bash
ops k8s rollouts abort api-server-v2 -n production
```

**Expected Output**:

```text
Rollout 'api-server-v2' aborted
Rolled back to previous stable version
```

**Troubleshooting**:

| Issue                       | Solution                                                                        |
| --------------------------- | ------------------------------------------------------------------------------- |
| Canary stuck in pause       | Check analysis status. Promote manually with `ops k8s rollouts promote <name>`. |
| Analysis continuously fails | Check metrics provider (Prometheus) connectivity. Verify                        |
| Promotion not progressing   | Verify enough nodes available for canary weight. Check resource                 |

---

## Certificate Management

### Managing TLS Certificates with Cert-Manager

**Context**: Create and manage TLS certificates using Cert-Manager with LetsEncrypt issuer and
monitor certificate renewal.

**Prerequisites**:

- Cert-Manager installed in cluster (`cert-manager` namespace)
- Valid domain name with DNS configured
- Ingress controller running

**Step 1: List Certificates**

View all certificates in the cluster:

```bash
ops k8s certs certificates list -A
```

**Expected Output**:

```text
NAMESPACE   NAME              ISSUER           STATUS    EXPIRATION
production  api.example.com   letsencrypt-prod Issued    2025-05-15T10:30:45Z
production  web.example.com   letsencrypt-prod Issued    2025-06-20T10:30:45Z
staging     app.example.com   letsencrypt-staging Issued 2025-04-10T10:30:45Z
```

**Step 2: Get Certificate Details**

View detailed information about a certificate:

```bash
ops k8s certs certificates get api.example.com -n production
```

**Expected Output**:

```text
Name:              api.example.com
Namespace:         production
Issuer:            letsencrypt-prod
Status:            Issued
Common Name:       api.example.com
SANs:              *.api.example.com
Issued At:         2024-02-16T10:30:45Z
Expiration Date:   2025-05-15T10:30:45Z
Days Until Expiry: 88d
Secret Name:       api-tls-cert
```

**Step 3: List Issuers**

View all available certificate issuers:

```bash
ops k8s certs issuers list -n production
```

**Expected Output**:

```text
NAME                   TYPE            STATUS    AGE
letsencrypt-prod       ClusterIssuer   Ready     180d
letsencrypt-staging    ClusterIssuer   Ready     180d
self-signed           ClusterIssuer   Ready     180d
```

**Step 4: Get Issuer Details**

View issuer configuration:

```bash
ops k8s certs issuers get letsencrypt-prod
```

**Expected Output**:

```text
Name:              letsencrypt-prod
Type:              ClusterIssuer
Status:            Ready
Provider:          acme
Email:             admin@example.com
ACME Server:       https://acme-v02.api.letsencrypt.org/directory
```

**Step 5: Create New Certificate**

Create a new certificate for a domain:

```bash
cat > certificate.yaml << 'EOF'
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: myapp.example.com
  namespace: production
spec:
  secretName: myapp-tls
  duration: 2160h  # 90 days
  renewBefore: 720h  # 30 days before expiry
  commonName: myapp.example.com
  dnsNames:
  - myapp.example.com
  - "*.myapp.example.com"
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
EOF

ops k8s manifest apply -f certificate.yaml
```

**Expected Output**:

```text
certificate.cert-manager.io/myapp.example.com created
```

**Step 6: Wait for Certificate Issuance**

Check certificate status during issuance:

```bash
ops k8s certs certificates get myapp.example.com -n production
```

Expected output during issuance (wait a few moments):

```text
Name:              myapp.example.com
Namespace:         production
Issuer:            letsencrypt-prod
Status:            Pending
Common Name:       myapp.example.com
Secret Name:       myapp-tls
Conditions:
  Issuing       Creating ACME order
```

Expected output after issuance (after a few moments):

```text
Name:              myapp.example.com
Namespace:         production
Issuer:            letsencrypt-prod
Status:            Issued
Common Name:       myapp.example.com
Issued At:         2024-02-16T10:45:30Z
Expiration Date:   2025-05-16T10:45:30Z
Days Until Expiry: 89d
Secret Name:       myapp-tls
```

**Step 7: Use Certificate in Ingress**

Reference the certificate in an ingress resource:

```bash
cat > ingress.yaml << 'EOF'
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: myapp
  namespace: production
spec:
  tls:
  - hosts:
    - myapp.example.com
    - "*.myapp.example.com"
    secretName: myapp-tls
  rules:
  - host: myapp.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: myapp
            port:
              number: 80
EOF

ops k8s manifest apply -f ingress.yaml
```

**Expected Output**:

```text
ingress.networking.k8s.io/myapp created
```

**Step 8: Monitor Certificate Renewal**

Check renewal status before expiry:

```bash
ops k8s certs certificates list -A | grep -E "NAMESPACE|api.example"
```

Expected output with renewal approaching:

```text
NAMESPACE   NAME              ISSUER           STATUS    EXPIRATION
production  api.example.com   letsencrypt-prod Issued    2025-03-15T10:30:45Z
```

**Troubleshooting**:

| Issue                        | Solution                                                                    |
| ---------------------------- | --------------------------------------------------------------------------- |
| Certificate stuck in Pending | Check DNS propagation with `nslookup _acme-challenge.domain.com`. View      |
| Certificate renewal fails    | Check Cert-Manager is updated. Verify issuer is healthy with `ops k8s certs |
| Domain validation failing    | Verify DNS records point to correct ingress IP. Check firewall allows       |

---

## Policy Enforcement with Kyverno

### Creating and Managing Policies

**Context**: Define policies to enforce organizational standards and validate resources
using Kyverno policy engine.

**Prerequisites**:

- Kyverno installed in cluster (`kyverno` namespace)
- kubectl access with admin permissions

**Step 1: List Existing Policies**

View all Kyverno policies:

```bash
ops k8s policies list -A
```

**Expected Output**:

```text
NAMESPACE   NAME                     TYPE      ACTION     STATUS
kyverno     require-image-registry    Cluster   validate   enabled
kyverno     restrict-sysctls         Cluster   validate   enabled
kyverno     require-labels           Cluster   validate   enabled
prod        allowed-registries       Namespaced audit     enabled
```

**Step 2: Get Policy Details**

View detailed information about a policy:

```bash
ops k8s policies get require-image-registry
```

**Expected Output**:

```text
Name:              require-image-registry
Type:              ClusterPolicy
Action:            validate
Status:            enabled
Rules:             2
Description:       Require container images from approved registries
```

**Step 3: Create Custom Policy**

Create a policy requiring image pulls from approved registries:

```bash
cat > registry-policy.yaml << 'EOF'
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-approved-registries
  namespace: kyverno
spec:
  validationFailureAction: audit
  rules:
  - name: check-image-registry
    match:
      resources:
        kinds:
        - Pod
        - Deployment
        - StatefulSet
    validate:
      message: "Images must be from approved registries"
      pattern:
        spec:
          =(containers):
          - image: "registry.example.com/* | gcr.io/*"
EOF

ops k8s manifest apply -f registry-policy.yaml
```

**Expected Output**:

```text
clusterpolicy.kyverno.io/require-approved-registries created
```

**Step 4: List Policy Reports**

View policy violation reports:

```bash
ops k8s policies policy-reports list -A
```

**Expected Output**:

```text
NAMESPACE   NAME                     POLICY        RESULTS   PASS   FAIL
production  policy-report-deployment require-labels 50        48     2
production  policy-report-statefulset require-labels 30        28     2
staging     policy-report-pods       restrict-hostpath 20    20     0
```

**Step 5: Get Policy Report Details**

View violations for a specific policy:

```bash
ops k8s policies policy-reports get policy-report-deployment -n production
```

**Expected Output**:

```text
Name:            policy-report-deployment
Namespace:       production
Policy:          require-labels
Pass:            48
Fail:            2
Skip:            0

Violations:
  RESOURCE           RULE           STATUS   MESSAGE
  my-app-abc123d     check-labels   fail     Missing required labels: team,env
  web-frontend-xyz99 check-labels   fail     Missing required labels: team
```

**Step 6: Create Audit Policy**

Create a policy in audit mode to report violations without blocking:

```bash
cat > audit-policy.yaml << 'EOF'
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-resource-limits
spec:
  validationFailureAction: audit
  rules:
  - name: check-limits
    match:
      resources:
        kinds:
        - Deployment
    validate:
      message: "CPU and memory limits are required"
      pattern:
        spec:
          template:
            spec:
              containers:
              - resources:
                  limits:
                    memory: "?*"
                    cpu: "?*"
EOF

ops k8s manifest apply -f audit-policy.yaml
```

**Expected Output**:

```text
clusterpolicy.kyverno.io/require-resource-limits created
```

**Step 7: Convert Policy to Enforcing**

Change policy from audit to enforce mode:

```bash
cat > enforce-policy.yaml << 'EOF'
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-approved-registries
  namespace: kyverno
spec:
  validationFailureAction: enforce
  rules:
  - name: check-image-registry
    match:
      resources:
        kinds:
        - Pod
        - Deployment
    validate:
      message: "Images must be from approved registries"
      pattern:
        spec:
          =(containers):
          - image: "registry.example.com/* | gcr.io/*"
EOF

ops k8s manifest apply -f enforce-policy.yaml
```

**Expected Output**:

```text
clusterpolicy.kyverno.io/require-approved-registries configured
```

**Troubleshooting**:

| Issue                           | Solution                                                                    |
| ------------------------------- | --------------------------------------------------------------------------- |
| Policy not blocking deployments | Check validationFailureAction is set to "enforce" not "audit". Verify       |
| High false positive rate        | Refine policy pattern to be more specific. Test pattern                     |
| Policy report not updating      | Check Kyverno is running with `ops k8s pods list -n kyverno`. Verify policy |

---

## TUI Walkthrough

### Interactive Terminal UI Exploration

**Context**: Launch and navigate the Terminal User Interface (TUI) for interactive cluster
exploration and resource management.

**Prerequisites**:

- Terminal supporting 256+ colors
- Kubernetes cluster accessible
- Python with curses library (standard in most Linux/macOS)

**Step 1: Launch TUI**

Start the interactive terminal UI:

```bash
ops k8s tui
```

**Expected Output**:

The terminal will display an interactive dashboard showing:

```text
╔════════════════════════════════════════════════════════════════════════════════╗
║                     Kubernetes Cluster Dashboard - minikube                    ║
╠════════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  Dashboard        Namespaces        Resources        Logs        Ecosystem     ║
║  ────────────────────────────────────────────────────────────────────────────  ║
║                                                                                ║
║  Cluster Status                                                                ║
║  ├─ Context: minikube                                                          ║
║  ├─ Version: v1.27.4                                                           ║
║  ├─ Nodes: 1 Ready                                                             ║
║  ├─ Namespaces: 7                                                              ║
║  └─ Pods: 18 Running, 0 Pending, 0 Failed                                      ║
║                                                                                ║
║  Quick Stats                                                                   ║
║  ├─ CPU Usage: 2.3 cores (28% of 8 available)                                  ║
║  ├─ Memory Usage: 3.2 Gi (40% of 8 Gi available)                               ║
║  └─ Storage Usage: 12.5 Gi (62% of 20 Gi available)                            ║
║                                                                                ║
╚════════════════════════════════════════════════════════════════════════════════╝

Navigation: Use arrow keys to navigate, Enter to select, Q to quit
```

**Step 2: Navigate to Namespaces Tab**

Press right arrow or click "Namespaces" tab:

```text
╔════════════════════════════════════════════════════════════════════════════════╗
║                    Kubernetes Cluster Dashboard - minikube                     ║
╠════════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  Dashboard        Namespaces        Resources        Logs        Ecosystem     ║
║  ────────────────────────────────────────────────────────────────────────────  ║
║                                                                                ║
║  Namespaces (7 total)                                                          ║
║  ┌──────────────────────┬────────┬────────┬───────────┬──────────────┐         ║
║  │ NAME                 │ STATUS │ PODS   │ CPU USED  │ MEMORY USED  │         ║
║  ├──────────────────────┼────────┼────────┼───────────┼──────────────┤         ║
║  │ default              │ Active │ 3      │ 100m      │ 256Mi        │         ║
║  │ kube-system          │ Active │ 9      │ 800m      │ 1.2Gi        │         ║
║  │ kube-node-lease      │ Active │ 1      │ 10m       │ 50Mi         │         ║
║  │ kube-public          │ Active │ 1      │ 20m       │ 64Mi         │         ║
║  │ kube-apiserver       │ Active │ 2      │ 150m      │ 512Mi        │         ║
║  │ production           │ Active │ 2      │ 250m      │ 512Mi        │         ║
║  │ staging              │ Active │ 0      │ 0m        │ 0Mi          │         ║
║  └──────────────────────┴────────┴────────┴───────────┴──────────────┘         ║
║                                                                                ║
║  Select a namespace to view resources:                                         ║
║  [A]ll namespaces, [P]roduction, [S]taging, [D]efault, or [Q]uit               ║
║                                                                                ║
╚════════════════════════════════════════════════════════════════════════════════╝
```

**Step 3: Navigate to Resources Tab**

Press right arrow or click "Resources" tab to explore resource types:

```text
╔════════════════════════════════════════════════════════════════════════════════╗
║                    Kubernetes Cluster Dashboard - minikube                     ║
╠════════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  Dashboard        Namespaces        Resources        Logs        Ecosystem     ║
║  ────────────────────────────────────────────────────────────────────────────  ║
║  Namespace: production                                                         ║
║                                                                                ║
║  Resource Types                                                                ║
║  ├─ Pods (2)                                                                   ║
║  │  ├─ my-app-abc123 (Running) - 100m CPU, 256Mi Memory                        ║
║  │  └─ my-app-def456 (Running) - 80m CPU, 200Mi Memory                         ║
║  ├─ Deployments (1)                                                            ║
║  │  └─ my-app (3/3 Ready) - 250m CPU limit, 512Mi Memory limit                 ║
║  ├─ Services (2)                                                               ║
║  │  ├─ my-app (ClusterIP) - 10.0.0.100:80                                      ║
║  │  └─ api-gateway (LoadBalancer) - 203.0.113.42:443                           ║
║  ├─ ConfigMaps (1)                                                             ║
║  │  └─ app-config - 3 keys                                                     ║
║  ├─ Secrets (2)                                                                ║
║  │  ├─ app-credentials - 3 keys                                                ║
║  │  └─ docker-registry - registry credentials                                  ║
║  └─ StatefulSets (0)                                                           ║
║                                                                                ║
║  Use [J]/[K] to navigate, [ENTER] to select, [Q] to quit                       ║
║                                                                                ║
╚════════════════════════════════════════════════════════════════════════════════╝
```

**Step 4: Select Pod to View Logs**

Navigate to Logs tab:

```text
╔════════════════════════════════════════════════════════════════════════════════╗
║                    Kubernetes Cluster Dashboard - minikube                     ║
╠════════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  Dashboard        Namespaces        Resources        Logs        Ecosystem     ║
║  ────────────────────────────────────────────────────────────────────────────  ║
║  Pod: my-app-abc123 (production)                                               ║
║                                                                                ║
║  [F]ollow logs  [C]lear screen  [T]ail 100 lines  [S]earch  [Q]uit             ║
║  ────────────────────────────────────────────────────────────────────────────  ║
║                                                                                ║
║  2024-02-16T10:30:45.123Z [INFO] Application started                           ║
║  2024-02-16T10:30:46.456Z [INFO] Server listening on 0.0.0.0:8080              ║
║  2024-02-16T10:30:47.789Z [INFO] Connected to database: postgres://db:5432     ║
║  2024-02-16T10:30:50.234Z [INFO] Cache initialized: redis://cache:6379         ║
║  2024-02-16T10:31:15.567Z [INFO] GET /health 200 45ms                          ║
║  2024-02-16T10:31:20.890Z [INFO] POST /api/users 201 234ms                     ║
║  2024-02-16T10:31:25.123Z [WARN] Slow query detected: 1.2s                     ║
║  2024-02-16T10:31:30.456Z [INFO] GET /api/users 200 89ms                       ║
║  2024-02-16T10:31:35.789Z [INFO] GET /api/users/123 200 45ms                   ║
║                                                                                ║
║  [F] - Follow (stream logs), [C] - Clear, [T] - Last 100, [S] - Search         ║
║                                                                                ║
╚════════════════════════════════════════════════════════════════════════════════╝
```

**Step 5: Navigate to Ecosystem Tab**

View integrated ecosystem tools:

```text
╔════════════════════════════════════════════════════════════════════════════════╗
║                    Kubernetes Cluster Dashboard - minikube                     ║
╠════════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  Dashboard        Namespaces        Resources        Logs        Ecosystem     ║
║  ────────────────────────────────────────────────────────────────────────────  ║
║                                                                                ║
║  Ecosystem Tools Status                                                        ║
║  ├─ Helm                                                  [AVAILABLE]          ║
║  │  ├─ Version: 3.12.1                                                         ║
║  │  ├─ Releases: 3 installed                                                   ║
║  │  └─ Repositories: 5 configured                                              ║
║  ├─ ArgoCD                                                [INSTALLED]          ║
║  │  ├─ Version: 2.8.0                                                          ║
║  │  ├─ Namespace: argocd                                                       ║
║  │  └─ Applications: 5 total (4 synced, 1 out-of-sync)                         ║
║  ├─ Kyverno                                               [INSTALLED]          ║
║  │  ├─ Version: 1.9.0                                                          ║
║  │  ├─ Namespace: kyverno                                                      ║
║  │  └─ Policies: 8 cluster policies, 3 violations                              ║
║  ├─ Cert-Manager                                          [INSTALLED]          ║
║  │  ├─ Version: 1.13.0                                                         ║
║  │  └─ Certificates: 5 issued, 0 pending                                       ║
║  ├─ Flux                                                  [INSTALLED]          ║
║  │  ├─ Version: 2.1.0                                                          ║
║  │  └─ Kustomizations: 3, HelmReleases: 2                                      ║
║  └─ Argo Rollouts                                         [NOT INSTALLED]      ║
║                                                                                ║
║  [H] - Helm, [A] - ArgoCD, [K] - Kyverno, [C] - Cert-Manager, [Q] - Quit       ║
║                                                                                ║
╚════════════════════════════════════════════════════════════════════════════════╝
```

**Step 6: TUI Keyboard Shortcuts**

Key shortcuts available in TUI:

| Key        | Action                                       |
| ---------- | -------------------------------------------- |
| Arrow Keys | Navigate between items and tabs              |
| Enter      | Select/expand item                           |
| [J]/[K]    | Down/up navigation (vi-style)                |
| [H]/[L]    | Previous/next tab (vi-style)                 |
| [F]        | Follow/stream logs (in Logs tab)             |
| [C]        | Clear screen                                 |
| [T]        | Tail last N lines                            |
| [S]        | Search in logs                               |
| [D]        | Describe selected resource                   |
| [Y]        | Delete selected resource (with confirmation) |
| [R]        | Refresh current view                         |
| [Q]        | Quit/go back                                 |

**Troubleshooting**:

| Issue                      | Solution                                                                       |
| -------------------------- | ------------------------------------------------------------------------------ |
| TUI doesn't display colors | Terminal doesn't support 256 colors. Try setting `export TERM=xterm-256color`. |
| Rendering glitches         | Try resizing terminal window. Refresh with [R] key. Update                     |
| Navigation is slow         | Reduce number of pods with namespace filters. Check                            |

---

## Resource Optimization

### Analyze Cluster and Apply Recommendations

**Context**: Identify inefficient resource usage and apply optimization recommendations
to improve cluster efficiency and reduce costs.

**Prerequisites**:

- Kubernetes cluster with running workloads
- Metrics server installed for resource metrics
- At least 1 hour of historical data available

**Step 1: Run Resource Analysis**

Analyze current resource usage across the cluster:

```bash
ops k8s optimize analyze
```

**Expected Output**:

```text
Analyzing cluster resources...

Cluster Summary:
├─ Total CPU Requested:     2000m (25% of 8 cores available)─────┤
├─ Total Memory Requested:  4.5Gi (56% of 8 Gi available)────────┤
├─ Pods with No Limits:     12 pods──────────────────────────────┤
├─ Pods with No Requests:   8 pods───────────────────────────────┤
├─ Overallocated Pods:      3 pods (using less than 10% requested┤
└─ Under-provisioned Pods:  1 pod (using 95% of limit)───────────┘

Namespace Breakdown:
├─ production  - CPU: 1200m, Memory: 2.8Gi───────────────────────┤
├─ staging     - CPU: 500m, Memory: 1.2Gi────────────────────────┤
├─ default     - CPU: 200m, Memory: 256Mi────────────────────────┤
└─ kube-system - CPU: 100m, Memory: 256Mi────────────────────────┘
```

**Step 2: Get Optimization Recommendations**

Review specific recommendations:

```bash
ops k8s optimize recommendations
```

**Expected Output**:

```text
Optimization Recommendations (24 total):

Priority: High
├─ [1] Pod: web-frontend (production)─────┤
│    Issue: No memory limits set          │
│    Recommendation: Set memory limit to 512Mi│
│    Expected Saving: 15% memory overhead reduction│
│                                         │
├─ [2] Pod: api-server (production)───────┤
│    Issue: Overallocated - uses 50m of 500m CPU│
│    Recommendation: Reduce CPU request to 100m│
│    Expected Saving: 80m CPU per pod, 240m total (3 replicas)│
│                                         │

Priority: Medium
├─ [3] Deployment: worker-jobs (staging)──┤
│    Issue: No liveness probe configured  │
│    Recommendation: Add liveness probe   │
│    Expected Impact: Improved reliability and pod restart handling│
│                                         │
├─ [4] StatefulSet: db-replica (production┤
│    Issue: Manual pod management detected│
│    Recommendation: Implement pod disruption budget│
│    Expected Impact: Better high availability│

Priority: Low
├─ [5] ConfigMap: unused-config (default)─┤
│    Issue: Not mounted by any pod        │
│    Recommendation: Delete unused ConfigMap│
│    Expected Saving: Negligible storage, improves cluster cleanliness│
```

**Step 3: Filter Recommendations by Type**

View specific types of recommendations:

```bash
ops k8s optimize recommendations --type resource-limits
```

**Expected Output**:

```text
Resource Limit Recommendations (8 total):

[1] Pod: web-frontend (production)
    Current: CPU limit not set, Memory limit not set
    Recommended: CPU limit 250m, Memory limit 512Mi
    Rationale: Similar pods average 180m CPU, 380Mi Memory

[2] Pod: background-worker (staging)
    Current: CPU 1000m, Memory 2Gi
    Recommended: CPU 500m, Memory 1Gi
    Rationale: Average usage is 280m CPU, 512Mi Memory
    Potential Saving: 500m CPU, 1Gi Memory per pod

[3] Pod: api-server (production)
    Current: CPU 500m, Memory 1Gi
    Recommended: CPU 250m, Memory 512Mi
    Rationale: Average usage is 120m CPU, 250Mi Memory
    Potential Saving: 1200m CPU, 2Gi Memory total (4 replicas)
```

**Step 4: Preview Recommendation Changes**

View what would change before applying:

```bash
ops k8s optimize recommendations --preview --format yaml
```

**Expected Output**:

```yaml
recommendations:
  - pod_name: web-frontend
    namespace: production
    changes:
      resources:
        limits:
          cpu: 250m
          memory: 512Mi
        requests:
          cpu: 100m
          memory: 256Mi
    estimated_savings:
      cpu: "150m"
      memory: "512Mi"

  - pod_name: api-server
    namespace: production
    changes:
      resources:
        limits:
          cpu: 250m
          memory: 512Mi
    estimated_savings:
      cpu: "1200m" # for all 4 replicas
      memory: "2Gi"

summary:
  total_recommendations: 24
  total_cpu_savings: "2800m"
  total_memory_savings: "5.5Gi"
  estimated_cost_reduction: "18%"
```

**Step 5: Apply Recommendations**

Apply recommended changes to the cluster:

```bash
ops k8s optimize apply --recommendations 1,2,3 --dry-run
```

**Expected Output (Dry Run)**:

```text
Dry-run: Resource changes that would be applied:

[1] Pod: web-frontend (production)
    Would update: limits.memory: null → 512Mi

[2] Pod: api-server (production)
    Would update: limits.cpu: 500m → 250m, limits.memory: 1Gi → 512Mi

[3] Deployment: worker-jobs (staging)
    Would add: livenessProbe (httpGet /health port 8080)

Summary:
  Resources to modify: 3
  Estimated downtime: 0 (rolling updates)

Proceed with changes? [y/N]:
```

Apply the changes:

```bash
ops k8s optimize apply --recommendations 1,2,3 --force
```

**Expected Output**:

```text
Applying recommendations...

[1/3] Updating pod: web-frontend (production)
      ✓ Memory limit set to 512Mi
      ✓ Pod restarted (no downtime)

[2/3] Updating pod: api-server (production)
      ✓ CPU limit reduced to 250m
      ✓ Memory limit set to 512Mi
      ✓ Deployment rolling update in progress (4 new pods starting)

[3/3] Adding liveness probe to: worker-jobs (staging)
      ✓ StatefulSet updated
      ✓ Rolling update starting (staggered restarts)

Summary:
  Successfully applied: 3 recommendations
  Estimated resource savings:
    - CPU: 2800m released
    - Memory: 5.5Gi released
  Estimated monthly cost reduction: $850
```

**Step 6: Monitor Changes**

Verify the changes took effect:

```bash
ops k8s optimize analyze
```

Expected output after optimization:

```text
Analyzing cluster resources...

Cluster Summary:
├─ Total CPU Requested:     1500m (19% of 8 cores available)  # Reduced from 2000┤
├─ Total Memory Requested:  2.5Gi (31% of 8 Gi available)   # Reduced from 4.5Gi─┤
├─ Pods with No Limits:     8 pods (down from 12)           # Improved───────────┤
├─ Pods with No Requests:   4 pods (down from 8)            # Improved───────────┤
├─ Overallocated Pods:      1 pod (down from 3)             # Improved───────────┤
└─ Under-provisioned Pods:  0 pods (down from 1)            # Fixed──────────────┘
```

**Troubleshooting**:

| Issue                           | Solution                                                                      |
| ------------------------------- | ----------------------------------------------------------------------------- |
| No metrics available            | Check metrics-server is running with `ops k8s pods list -n kube-system`. Wait |
| Recommendations seem wrong      | View actual usage with `kubectl top nodes` and `kubectl top                   |
| Apply fails with quota exceeded | Check namespace resource quotas with `ops k8s describe                        |

---

## Manifest Management

### Validating, Diffing, and Applying Manifests

**Context**: Manage Kubernetes manifests safely by validating YAML, diffing against cluster,
and applying changes with preview.

**Prerequisites**:

- Kubernetes manifests in YAML format
- Cluster connectivity with appropriate RBAC permissions

**Step 1: Create Sample Manifest**

Create a manifest file for validation:

```bash
cat > my-app.yaml << 'EOF'
---
apiVersion: v1
kind: Namespace
metadata:
  name: my-app

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: my-app
data:
  app.env: |
    LOG_LEVEL=info
    DATABASE_URL=postgres://db:5432/myapp

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: my-app
  labels:
    app: my-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: app
        image: myapp:v1.0
        ports:
        - containerPort: 8080
        env:
        - name: CONFIG_PATH
          value: /etc/config/app.env
        volumeMounts:
        - name: config
          mountPath: /etc/config
      volumes:
      - name: config
        configMap:
          name: app-config

---
apiVersion: v1
kind: Service
metadata:
  name: my-app
  namespace: my-app
spec:
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080
  type: ClusterIP
EOF
```

**Step 2: Validate Manifest Syntax**

Check manifest for YAML and schema errors:

```bash
ops k8s manifest validate -f my-app.yaml
```

**Expected Output**:

```text
Validation Results: my-app.yaml
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Format Version:    v1
Documents:         4
Resources:         4
  - Namespace: 1
  - ConfigMap: 1
  - Deployment: 1
  - Service: 1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Status:            VALID

All resources are syntactically correct and conform to Kubernetes schema.
```

**Step 3: Dry-Run Apply (Client-Side Validation)**

Validate against cluster (client-side):

```bash
ops k8s manifest apply -f my-app.yaml --dry-run=client
```

**Expected Output**:

```text
Dry-run (client-side): Resources that would be created:

namespace/my-app created (dry run)
configmap/app-config created (dry run)
deployment.apps/my-app created (dry run)
service/my-app created (dry run)

Summary: 4 resources would be created
Status: OK - No validation errors
```

**Step 4: Dry-Run with Server Validation**

Validate against cluster (server-side):

```bash
ops k8s manifest apply -f my-app.yaml --dry-run=server
```

**Expected Output**:

```text
Dry-run (server-side): Validation against cluster:

namespace/my-app created (dry run)
  ✓ Namespace name is available
  ✓ User has permission to create namespaces

configmap/app-config created (dry run)
  ✓ ConfigMap schema is valid
  ✓ Data format is correct

deployment.apps/my-app created (dry run)
  ✓ Deployment schema is valid
  ✓ Container image reference is valid format
  ✓ Volume names referenced in template exist
  ✓ Port number valid (8080)

service/my-app created (dry run)
  ✓ Service schema is valid
  ✓ Selector matches deployment template labels
  ✓ TargetPort matches container port (8080)

Summary: 4 resources validated successfully
Status: OK - Ready to apply
```

**Step 5: Diff Against Current Cluster State**

Compare manifest with current cluster state:

```bash
ops k8s manifest diff -f my-app.yaml
```

**Expected Output (Manifest Doesn't Exist Yet)**:

```text
Configuration Diff: my-app.yaml vs Current Cluster State
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Namespaces:
  + my-app (new)

ConfigMaps (my-app):
  + app-config (new)

Deployments (my-app):
  + my-app (new)
    + replicas: 3
    + image: myapp:v1.0
    + ports: [8080]

Services (my-app):
  + my-app (new)
    + type: ClusterIP
    + port: 80 -> 8080

Summary: 4 additions, 0 modifications, 0 removals
Status: All resources are new
```

**Step 6: Apply Manifest**

Apply the manifest to the cluster:

```bash
ops k8s manifest apply -f my-app.yaml
```

**Expected Output**:

```text
Applying manifest: my-app.yaml

namespace/my-app created
configmap/app-config created
deployment.apps/my-app created
service/my-app created

Summary: 4 resources created
Status: Successfully applied
```

**Step 7: Update Manifest and Diff Again**

Update the manifest with new changes:

```bash
cat > my-app.yaml << 'EOF'
---
apiVersion: v1
kind: Namespace
metadata:
  name: my-app

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: my-app
data:
  app.env: |
    LOG_LEVEL=debug
    DATABASE_URL=postgres://db:5432/myapp
    CACHE_ENABLED=true

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: my-app
  labels:
    app: my-app
spec:
  replicas: 5
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: app
        image: myapp:v1.1
        ports:
        - containerPort: 8080
        env:
        - name: CONFIG_PATH
          value: /etc/config/app.env
        volumeMounts:
        - name: config
          mountPath: /etc/config
      volumes:
      - name: config
        configMap:
          name: app-config

---
apiVersion: v1
kind: Service
metadata:
  name: my-app
  namespace: my-app
spec:
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080
  type: LoadBalancer
EOF

ops k8s manifest diff -f my-app.yaml
```

**Expected Output**:

```text
Configuration Diff: my-app.yaml vs Current Cluster State
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ConfigMaps (my-app):
  ~ app-config (modified)
    ~ data.app.env:
      - LOG_LEVEL=info
      + LOG_LEVEL=debug
      + CACHE_ENABLED=true

Deployments (my-app):
  ~ my-app (modified)
    ~ replicas: 3 -> 5
    ~ image: myapp:v1.0 -> myapp:v1.1

Services (my-app):
  ~ my-app (modified)
    ~ type: ClusterIP -> LoadBalancer

Summary: 0 additions, 3 modifications, 0 removals
Status: Updates pending
```

**Step 8: Apply Updated Manifest**

Apply the changes:

```bash
ops k8s manifest apply -f my-app.yaml --confirm
```

**Expected Output**:

```text
Applying updated manifest: my-app.yaml

configmap/app-config configured
deployment.apps/my-app configured
service/my-app configured

Summary: 0 created, 3 updated, 0 deleted
Status: Successfully applied

Rolling Update Progress:
  Deployment: my-app
  Old Replicas: 3 -> 0
  New Replicas: 0 -> 5
  Progressing: 2/5 ready
```

**Troubleshooting**:

| Issue                              | Solution                                                                 |
| ---------------------------------- | ------------------------------------------------------------------------ |
| Validation fails with schema error | Check Kubernetes API version for resource type. Verify all required      |
| Diff shows unexpected changes      | Run `kubectl diff -f manifest.yaml` for comparison. Check if other tools |
| Apply fails with permission denied | Check RBAC permissions with `kubectl auth can-i                          |

---

## See Also

- [Core Commands](./commands/core.md) - Cluster management and status
- [Workloads Commands](./commands/workloads.md) - Pod and deployment management
- [Networking Commands](./commands/networking.md) - Service and ingress management
- [Configuration & Storage](./commands/configuration-storage.md) - ConfigMaps, secrets, volumes
- [RBAC Commands](./commands/rbac.md) - Role-based access control
- [Job Commands](./commands/jobs.md) - Job and CronJob management
- [Helm Integration](./ecosystem/helm.md) - Package management
- [ArgoCD Integration](./ecosystem/argocd.md) - GitOps operations
- [Kubernetes Plugin Index](./index.md) - Complete documentation
- [Troubleshooting Guide](./troubleshooting.md) - Problem diagnosis and solutions
