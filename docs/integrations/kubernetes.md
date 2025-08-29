# Kubernetes Integration

Comprehensive integration with Kubernetes clusters for container
orchestration, deployment management, and cloud-native operations.

## Overview

Kubernetes integration features:

- **Multi-Cluster Support**: Manage multiple Kubernetes clusters
- **Native Resource Management**: Direct manipulation of K8s resources
- **Deployment Strategies**: Advanced deployment patterns (rolling, blue-green, canary)
- **Service Mesh Integration**: Istio, Linkerd, and Consul Connect support
- **RBAC Management**: Role-based access control configuration
- **Custom Resource Definitions**: Support for CRDs and operators

## Configuration

### Cluster Configuration

```yaml
# config/kubernetes.yaml
kubernetes:
  clusters:
    development:
      context: "dev-cluster"
      kubeconfig: "~/.kube/config"
      namespace: "development"

    staging:
      context: "staging-cluster"
      kubeconfig: "~/.kube/staging-config"
      namespace: "staging"

    production:
      context: "prod-cluster"
      kubeconfig: "~/.kube/prod-config"
      namespace: "production"

  defaults:
    timeout: "300s"
    retry_attempts: 3
    dry_run_strategy: "server"

  features:
    metrics_server: true
    service_mesh: "istio"
    ingress_controller: "nginx"
    storage_class: "fast-ssd"
```

### Authentication

```yaml
# Authentication methods
auth:
  # Service Account Token
  service_account:
    token_file: "/var/run/secrets/kubernetes.io/serviceaccount/token"

  # OIDC Integration
  oidc:
    issuer_url: "https://auth.company.com"
    client_id: "kubernetes-client"
    client_secret_env: "OIDC_CLIENT_SECRET"

  # Certificate Authentication
  certificate:
    cert_file: "/etc/kubernetes/pki/client.crt"
    key_file: "/etc/kubernetes/pki/client.key"
    ca_file: "/etc/kubernetes/pki/ca.crt"

  # Token Authentication
  token:
    token_env: "KUBERNETES_TOKEN"
```

## Core Commands

### Cluster Management

```bash
# List clusters
sysctl k8s clusters

# Switch cluster context
sysctl k8s use-context production

# Cluster status
sysctl k8s cluster-info --context production

# Node information
sysctl k8s nodes --context production
```

### Resource Management Commands

```bash
# List resources
sysctl k8s get pods --namespace production
sysctl k8s get services --all-namespaces
sysctl k8s get deployments --selector app=api

# Describe resources
sysctl k8s describe deployment api --namespace production

# Resource logs
sysctl k8s logs api-deployment --follow --namespace production

# Execute commands in pods
sysctl k8s exec api-pod-123 --command "bash" --namespace production
```

## Deployment Management

### Kubernetes Deployments

```yaml
# deployments/api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: production
  labels:
    app: api
    version: v2.1.0
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
        version: v2.1.0
    spec:
      containers:
        - name: api
          image: registry.company.com/api:v2.1.0
          ports:
            - containerPort: 8080
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: api-secrets
                  key: database-url
          resources:
            requests:
              memory: "128Mi"
              cpu: "100m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 5
```

### Deployment Commands

```bash
# Deploy using kubectl apply
sysctl k8s apply --filename deployments/api-deployment.yaml --namespace production

# Deploy with System Control CLI
sysctl deploy api --env production --k8s-manifest deployments/api-deployment.yaml

# Rolling update
sysctl k8s rollout restart deployment/api --namespace production

# Check rollout status
sysctl k8s rollout status deployment/api --namespace production

# Rollback deployment
sysctl k8s rollout undo deployment/api --namespace production
```

## Service Mesh Integration

### Istio Configuration

```yaml
# service-mesh/istio-config.yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: api
  namespace: production
spec:
  hosts:
    - api.company.com
  http:
    - match:
        - headers:
            canary:
              exact: "true"
      route:
        - destination:
            host: api
            subset: canary
          weight: 100
    - route:
        - destination:
            host: api
            subset: stable
          weight: 90
        - destination:
            host: api
            subset: canary
          weight: 10

---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: api
  namespace: production
spec:
  host: api
  subsets:
    - name: stable
      labels:
        version: v2.0.0
    - name: canary
      labels:
        version: v2.1.0
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 10
        maxRequestsPerConnection: 2
    loadBalancer:
      simple: LEAST_CONN
    outlierDetection:
      consecutive5xxErrors: 3
      interval: 30s
      baseEjectionTime: 30s
```

### Service Mesh Commands

```bash
# Deploy with Istio sidecar injection
sysctl k8s apply --filename api-deployment.yaml --istio-inject

# Configure traffic splitting
sysctl traffic split api --canary 10 --stable 90 --namespace production

# Monitor service mesh metrics
sysctl k8s metrics istio --service api --duration 1h

# Service mesh troubleshooting
sysctl k8s debug istio --service api --check-configuration
```

## Monitoring and Observability

### Prometheus Integration

```yaml
# monitoring/prometheus-config.yaml
apiVersion: v1
kind: ServiceMonitor
metadata:
  name: api-monitor
  namespace: production
spec:
  selector:
    matchLabels:
      app: api
  endpoints:
    - port: metrics
      interval: 30s
      path: /metrics

---
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: api-alerts
  namespace: production
spec:
  groups:
    - name: api.rules
      rules:
        - alert: APIHighErrorRate
          expr: rate(http_requests_total{job="api",status=~"5.."}[5m]) > 0.1
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "High error rate on API service"
            description: "Error rate is {{ $value }} errors per second"

        - alert: APIHighLatency
          expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{job="api"}[5m])) > 0.5
          for: 10m
          labels:
            severity: warning
          annotations:
            summary: "High latency on API service"
            description: "95th percentile latency is {{ $value }}s"
```

### Monitoring Commands

```bash
# Deploy monitoring stack
sysctl k8s apply --filename monitoring/ --namespace monitoring

# Check metrics collection
sysctl k8s get servicemonitors --namespace production

# View Prometheus targets
sysctl monitor prometheus targets --namespace monitoring

# Export metrics
sysctl k8s metrics export --service api --duration 24h --format json
```

## Storage and StatefulSets

### Persistent Volume Configuration

```yaml
# storage/postgres-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: production
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
        - name: postgres
          image: postgres:15
          env:
            - name: POSTGRES_DB
              value: "app_prod"
            - name: POSTGRES_USER
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: username
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: password
          ports:
            - containerPort: 5432
          volumeMounts:
            - name: postgres-data
              mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
    - metadata:
        name: postgres-data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: "fast-ssd"
        resources:
          requests:
            storage: 100Gi
```

### Storage Commands

```bash
# List persistent volumes
sysctl k8s get pv --sort-by=.metadata.creationTimestamp

# Check storage classes
sysctl k8s get storageclass

# Backup persistent volume
sysctl k8s backup pvc postgres-data --namespace production

# Resize persistent volume
sysctl k8s resize pvc postgres-data --size 200Gi --namespace production
```

## Security and RBAC

### RBAC Configuration

```yaml
# rbac/system-control-rbac.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: system-control-operator
rules:
  - apiGroups: [""]
    resources: ["pods", "services", "endpoints", "configmaps", "secrets"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
  - apiGroups: ["apps"]
    resources: ["deployments", "statefulsets", "daemonsets"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
  - apiGroups: ["networking.k8s.io"]
    resources: ["ingresses", "networkpolicies"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: system-control-operator
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: system-control-operator
subjects:
  - kind: ServiceAccount
    name: system-control
    namespace: system-control
```

### Security Commands

```bash
# Create service account
sysctl k8s create serviceaccount system-control --namespace system-control

# Apply RBAC configuration
sysctl k8s apply --filename rbac/system-control-rbac.yaml

# Check permissions
sysctl k8s auth can-i create deployments --namespace production

# Scan for security issues
sysctl k8s security-scan --namespace production
```

## Custom Resource Definitions

### CRD Example

```yaml
# crds/application-crd.yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: applications.system-control.io
spec:
  group: system-control.io
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              properties:
                name:
                  type: string
                version:
                  type: string
                replicas:
                  type: integer
                  minimum: 1
                image:
                  type: string
                environment:
                  type: object
            status:
              type: object
              properties:
                phase:
                  type: string
                replicas:
                  type: integer
                ready:
                  type: integer
  scope: Namespaced
  names:
    plural: applications
    singular: application
    kind: Application
```

### CRD Management

```bash
# Apply CRD
sysctl k8s apply --filename crds/application-crd.yaml

# Create custom resource
sysctl k8s apply --filename examples/my-application.yaml

# List custom resources
sysctl k8s get applications --namespace production

# Watch custom resources
sysctl k8s get applications --watch --namespace production
```

## Networking

### Ingress Configuration

```yaml
# networking/api-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
  namespace: production
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
    - hosts:
        - api.company.com
      secretName: api-tls
  rules:
    - host: api.company.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: api
                port:
                  number: 80
```

### Network Policies

```yaml
# networking/api-network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
        - namespaceSelector:
            matchLabels:
              name: monitoring
      ports:
        - protocol: TCP
          port: 8080
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: database
      ports:
        - protocol: TCP
          port: 5432
    - to: []
      ports:
        - protocol: TCP
          port: 443
        - protocol: TCP
          port: 53
        - protocol: UDP
          port: 53
```

## Advanced Features

### Multi-Cluster Management

```bash
# List all clusters
sysctl k8s clusters list

# Deploy across multiple clusters
sysctl k8s deploy api --clusters "staging,production" --strategy parallel

# Sync resources between clusters
sysctl k8s sync --from production --to staging --resources deployments,services

# Multi-cluster monitoring
sysctl k8s monitor --clusters all --metrics cpu,memory,network
```

### GitOps Integration

```yaml
# gitops/argocd-application.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: api-application
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://git.company.com/k8s-manifests
    targetRevision: HEAD
    path: production/api
  destination:
    server: https://kubernetes.default.svc
    namespace: production
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

## Troubleshooting

### Common Issues

```bash
# Pod troubleshooting
sysctl k8s debug pod api-pod-123 --namespace production

# Service connectivity issues
sysctl k8s debug service api --namespace production

# DNS resolution problems
sysctl k8s debug dns --namespace production

# Resource constraints
sysctl k8s debug resources --namespace production

# Network policy issues
sysctl k8s debug network-policy --namespace production
```

### Performance Optimization

```bash
# Resource usage analysis
sysctl k8s analyze resources --namespace production --duration 7d

# Performance recommendations
sysctl k8s optimize --namespace production --recommendations

# Cluster capacity planning
sysctl k8s capacity-plan --growth-rate 20% --duration 6m

# Cost optimization
sysctl k8s cost-optimize --namespace production --recommendations
```

## Best Practices

### Resource Management Best Practices

1. **Resource Limits**: Always set resource requests and limits
2. **Health Checks**: Implement liveness and readiness probes
3. **Security Context**: Use non-root containers and security contexts
4. **Secrets Management**: Never hardcode secrets in manifests
5. **Namespace Isolation**: Use namespaces for environment separation

### Deployment Strategies

```yaml
# Best practices deployment template
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  labels:
    app.kubernetes.io/name: api
    app.kubernetes.io/version: "2.1.0"
    app.kubernetes.io/component: backend
    app.kubernetes.io/part-of: system-control
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
        - name: api
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop:
                - ALL
          resources:
            requests:
              memory: "128Mi"
              cpu: "100m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 30
          readinessProbe:
            httpGet:
              path: /ready
              port: 8080
            initialDelaySeconds: 5
```
