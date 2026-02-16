# Kubernetes Plugin > Troubleshooting

[< Back to Index](./index.md) | [Commands](./commands/) | [Ecosystem](./ecosystem/) | [Examples](./examples.md) | [TUI](./tui.md)

---

## Table of Contents

- [Connection Issues](#connection-issues)
- [Authentication Failures](#authentication-failures)
- [Multi-Cluster Problems](#multi-cluster-problems)
- [Namespace Issues](#namespace-issues)
- [Ecosystem Tool Detection](#ecosystem-tool-detection)
- [TUI Issues](#tui-issues)
- [Resource Operations](#resource-operations)
- [Common Error Messages](#common-error-messages)
- [Diagnostic Commands](#diagnostic-commands)
- [Environment Variable Conflicts](#environment-variable-conflicts)
- [Performance and Timeouts](#performance-and-timeouts)
- [RBAC and Permissions](#rbac-and-permissions)

---

## Connection Issues

### Cluster Unreachable

**Symptoms**: Connection refused, timeout, or unable to connect to cluster

**Cause**:

- Kubernetes API server is not accessible from your machine
- Network connectivity is broken
- Incorrect API server address in kubeconfig
- Firewall blocking connections to the API port
- Kubernetes cluster is not running

**Solution**:

1. Verify the cluster is running:

```bash
# For minikube
minikube status

# For Kind
kind get clusters

# For EKS
aws eks describe-cluster --name <cluster-name> --query 'cluster.status'

# For GKE
gcloud container clusters describe <cluster-name>

# For AKS
az aks show --resource-group <rg> --name <cluster-name> --query provisioningState
```

1. Check kubeconfig path and validity:

```bash
echo $KUBECONFIG
ls -la ~/.kube/config
cat ~/.kube/config | head -20
```

1. Verify API server endpoint:

```bash
kubectl config view --minify
```

**Expected Output**:

```yaml
apiVersion: v1
clusters:
  - cluster:
      certificate-authority-data: LS0tLS1CRUdJTi...
      server: https://10.0.0.1:6443
    name: my-cluster
```

1. Test connectivity directly:

```bash
# For HTTPS with certificate verification
curl -k https://10.0.0.1:6443/api/v1

# Check DNS resolution
nslookup kubernetes.default.svc.cluster.local
dig api.example.com
```

1. Check firewall and network:

```bash
# Test if port is open
nc -zv 10.0.0.1 6443
telnet 10.0.0.1 6443

# Check routing
traceroute 10.0.0.1
```

1. Verify with ops CLI:

```bash
ops k8s status --output json
```

If still failing, check logs and retry with increased timeout:

```bash
OPS_K8S_TIMEOUT=30 ops k8s status
```

---

### DNS Resolution Failed

**Symptoms**: Error message mentions "Name or service not known" or "nodename nor servname provided"

**Cause**:

- DNS server not resolving the Kubernetes API endpoint
- Incorrect domain name in kubeconfig
- Network DNS is misconfigured
- VPN not connected (if required)

**Solution**:

1. Check DNS resolution:

```bash
# Resolve the API server hostname
nslookup api.example.com
dig api.example.com
host api.example.com

# Check configured DNS
cat /etc/resolv.conf
```

1. Verify kubeconfig has correct server address:

```bash
kubectl config view
```

1. Try connecting with IP address instead:

```bash
# Edit kubeconfig to use IP instead of hostname
sed -i 's/api.example.com/10.0.0.1/g' ~/.kube/config
ops k8s status
```

1. Check network connectivity:

```bash
# Ping the API server (if ICMP allowed)
ping api.example.com

# Use alternative DNS
OPS_K8S_KUBECONFIG=~/.kube/config ops k8s status
```

1. For VPN users:

```bash
# Verify VPN is connected
ifconfig | grep -E "tun|vpn"

# Reconnect VPN
vpn-command connect
ops k8s status
```

---

### Timeout Errors

**Symptoms**: Command hangs or returns "i/o timeout" after waiting

**Cause**:

- Cluster is slow or overloaded
- Network latency is high
- API server is not responding
- Firewall is dropping packets
- Default timeout is too short

**Solution**:

1. Increase timeout for single command:

```bash
OPS_K8S_TIMEOUT=60 ops k8s pods list
OPS_K8S_TIMEOUT=120 ops k8s manifest apply -f manifest.yaml
```

1. Update configuration with longer timeout:

```bash
cat >> ~/.config/ops/config.yaml << 'EOF'
plugins:
  kubernetes:
    defaults:
      timeout: 600  # 10 minutes
EOF
```

1. Check cluster performance:

```bash
# Check API server latency
kubectl cluster-info dump | grep latency

# Monitor cluster resources
ops k8s nodes list
ops k8s top nodes
ops k8s top pods
```

1. Check network latency:

```bash
# Measure latency to API server
ping -c 3 api.example.com
mtr api.example.com

# Check network path
traceroute api.example.com
```

1. If cluster is overloaded, wait and retry:

```bash
# Wait 30 seconds
sleep 30
ops k8s status
```

1. For persistent timeouts, contact cluster administrator:

```bash
# Gather diagnostic information
ops k8s status --output json > diagnostics.json
kubectl cluster-info dump --output-directory=./cluster-dump
```

---

### Proxy/Firewall Issues

**Symptoms**: Connection fails through proxy or corporate firewall

**Cause**:

- Corporate proxy intercepting HTTPS
- Firewall rules blocking API server port
- SSL/TLS inspection enabled
- Proxy authentication required

**Solution**:

1. Check if proxy is configured:

```bash
echo $HTTP_PROXY
echo $HTTPS_PROXY
echo $NO_PROXY
```

1. Configure proxy in ops config:

```bash
cat > ~/.config/ops/config.yaml << 'EOF'
plugins:
  kubernetes:
    proxy:
      http: http://proxy.example.com:8080
      https: http://proxy.example.com:8080
      no_proxy: "localhost,127.0.0.1,*.internal"
EOF
```

1. Test proxy connectivity:

```bash
# Using curl through proxy
curl -x http://proxy.example.com:8080 https://api.example.com

# Check if proxy requires authentication
curl -x http://user:pass@proxy.example.com:8080 https://api.example.com
```

1. Disable SSL verification if trusted:

```bash
cat > ~/.config/ops/config.yaml << 'EOF'
plugins:
  kubernetes:
    auth:
      insecure_skip_tls_verify: true
EOF
```

1. Add certificate to trusted store:

```bash
# Export proxy certificate
openssl s_client -connect proxy.example.com:8080 -showcerts > proxy-cert.pem

# Add to system certificate store
sudo cp proxy-cert.pem /usr/local/share/ca-certificates/
sudo update-ca-certificates

# Or use in kubeconfig
kubectl config set clusters.my-cluster.certificate-authority=/path/to/proxy-cert.pem
```

---

## Authentication Failures

### Expired Credentials

**Symptoms**: 401 Unauthorized or "invalid credentials" errors

**Cause**:

- Kubeconfig credentials have expired
- OAuth token has expired
- Service account token is revoked
- Credentials need to be refreshed

**Solution**:

1. Check credential expiration:

```bash
kubectl config view
openssl x509 -in ~/.kube/config -text -noout | grep -A2 Validity
```

1. Refresh kubeconfig:

```bash
# AWS EKS
aws eks update-kubeconfig --name my-cluster --region us-east-1

# Google GKE
gcloud container clusters get-credentials my-cluster --zone us-central1-a

# Azure AKS
az aks get-credentials --resource-group my-group --name my-cluster

# Minikube
minikube update-context
```

1. Generate new token if using token auth:

```bash
# For service account token
kubectl create serviceaccount automation-user
kubectl create clusterrolebinding automation-admin \
  --clusterrole=admin \
  --serviceaccount=default:automation-user

TOKEN=$(kubectl get secret -n default $(kubectl get secret -n default | grep automation-user-token | awk '{print $1}') -o jsonpath='{.data.token}' | base64 -d)
export OPS_K8S_TOKEN=$TOKEN
```

1. Update ops configuration:

```bash
cat > ~/.config/ops/config.yaml << 'EOF'
plugins:
  kubernetes:
    auth:
      type: "kubeconfig"
    clusters:
      dev:
        kubeconfig: "~/.kube/config"
        context: "minikube"
EOF
```

1. Verify authentication:

```bash
ops k8s status
kubectl auth can-i get pods --all-namespaces
```

---

### Invalid Kubeconfig

**Symptoms**: "Unable to read kubeconfig", "auth-provider not found", or malformed YAML errors

**Cause**:

- Kubeconfig file is corrupted or has syntax errors
- File permissions are wrong
- Path contains special characters or spaces
- YAML formatting is invalid
- Auth provider plugin is missing

**Solution**:

1. Validate kubeconfig syntax:

```bash
kubectl config view
yaml-lint ~/.kube/config
python -m yaml ~/.kube/config
```

1. Check file exists and is readable:

```bash
ls -la ~/.kube/config
cat ~/.kube/config | head -10
```

1. Backup and regenerate kubeconfig:

```bash
# Backup current
cp ~/.kube/config ~/.kube/config.backup

# Regenerate for AWS EKS
aws eks update-kubeconfig --name my-cluster

# Or for GKE
gcloud container clusters get-credentials my-cluster
```

1. Fix YAML formatting:

```bash
# Check specific line causing error
head -20 ~/.kube/config | tail -5

# Validate YAML structure
cat ~/.kube/config | python -c "import sys, yaml; yaml.safe_load(sys.stdin)"
```

1. Verify auth provider is installed:

```bash
# For AWS IAM auth
aws-iam-authenticator version

# For Azure
azure-cli version

# For GKE
gcloud version
```

1. Check kubeconfig path in ops config:

```bash
cat ~/.config/ops/config.yaml | grep kubeconfig
cat ~/.config/ops/config.yaml | grep auth
```

---

### Certificate Errors

**Symptoms**: "certificate verify failed", "x509" errors, "self-signed certificate"

**Cause**:

- Self-signed certificate not trusted
- Certificate has expired
- Incorrect CA certificate
- Certificate chain is incomplete
- Man-in-the-middle attack (suspicious)

**Solution**:

1. Check certificate validity:

```bash
# For HTTPS endpoint
echo | openssl s_client -connect api.example.com:6443 | openssl x509 -text -noout | grep -E "Issuer|Validity|Subject"

# For kubeconfig
kubectl config view
cat ~/.kube/config | grep certificate-authority
```

1. Add CA certificate:

```bash
# Download CA certificate
openssl s_client -connect api.example.com:6443 -showcerts > ca.pem

# Add to kubeconfig
kubectl config set clusters.my-cluster.certificate-authority=./ca.pem
```

1. Skip TLS verification (for testing only):

```bash
# Update ops config
cat > ~/.config/ops/config.yaml << 'EOF'
plugins:
  kubernetes:
    auth:
      insecure_skip_tls_verify: true
EOF

# Test
ops k8s status
```

1. Verify certificate chain:

```bash
openssl s_client -connect api.example.com:6443 -showcerts | openssl x509 -text
```

1. For expired certificates:

```bash
# Check expiration
kubectl config view | grep certificate
echo | openssl s_client -connect api.example.com:6443 | grep -E "notBefore|notAfter"

# Regenerate if self-signed
kubeadm certs renew all  # If you have admin access
```

---

### RBAC Denied/Permission Errors

**Symptoms**: "forbidden", "no permission", "cluster-admin", or "verb not allowed" errors

**Cause**:

- User or service account lacks required RBAC permissions
- Role does not have required verbs
- RoleBinding or ClusterRoleBinding missing
- Wrong namespace specified

**Solution**:

1. Check current permissions:

```bash
kubectl auth can-i get pods
kubectl auth can-i get pods -n production
kubectl auth can-i create deployments --list
```

1. Check service account/user identity:

```bash
kubectl auth whoami
kubectl config current-context
kubectl config view --minify
```

1. View current roles and bindings:

```bash
# For namespace
ops k8s roles list -n production
ops k8s rolebindings list -n production

# For cluster
ops k8s clusterroles list
ops k8s clusterrolebindings list
```

1. Request required permissions from admin:

```bash
# Example: request read access to pods
# Contact cluster admin with this request

kubectl describe clusterrole view
kubectl describe clusterrole edit
kubectl describe clusterrole admin
```

1. Create temporary admin binding (if you have permissions):

```bash
# Grant cluster-admin to current user
kubectl create clusterrolebinding temp-admin \
  --clusterrole=cluster-admin \
  --user=$(kubectl config current-context)
```

1. Test with different context:

```bash
# List available contexts
ops k8s contexts

# Switch to different context with more permissions
ops k8s use-context prod-admin

# Try command again
ops k8s pods list
```

---

## Multi-Cluster Problems

### Context Not Found

**Symptoms**: "context 'prod-cluster' not found" or "current-context is not set"

**Cause**:

- Context name doesn't exist in kubeconfig
- Context name is misspelled
- Wrong kubeconfig file is being used
- Context was deleted or never created

**Solution**:

1. List available contexts:

```bash
ops k8s contexts
kubectl config get-contexts
```

1. Verify context name:

```bash
# View kubeconfig
cat ~/.kube/config | grep "name:"

# Search for specific context
grep -A2 "contexts:" ~/.kube/config
```

1. Use correct context name:

```bash
# If context exists
ops k8s use-context production-cluster

# View exact names
kubectl config view -o json | jq '.contexts[].name'
```

1. Check which kubeconfig is being used:

```bash
echo $KUBECONFIG
kubectl config view
cat ~/.kube/config | head -5
```

1. Create missing context if needed:

```bash
# Create new context
kubectl config set-context my-prod-context \
  --cluster=prod-cluster \
  --user=admin \
  --namespace=default

# Verify
ops k8s contexts
```

---

### Wrong Cluster Selected

**Symptoms**: Commands run against unexpected cluster or namespace

**Cause**:

- Active context pointing to wrong cluster
- OPS_K8S_CONTEXT environment variable overriding config
- Configuration has wrong context name
- Terminal session has stale context

**Solution**:

1. Check which cluster is active:

```bash
ops k8s status
kubectl config current-context
```

1. View all cluster information:

```bash
ops k8s contexts
kubectl config get-contexts
```

1. Switch to correct cluster:

```bash
ops k8s use-context staging-cluster
ops k8s status  # Verify
```

1. Check environment variable override:

```bash
echo $OPS_K8S_CONTEXT
echo $OPS_K8S_NAMESPACE

# Unset if needed
unset OPS_K8S_CONTEXT
unset OPS_K8S_NAMESPACE
```

1. Check ops configuration:

```bash
cat ~/.config/ops/config.yaml | grep -A10 kubernetes
cat ~/.config/ops/config.yaml | grep active_cluster
```

1. Force specific cluster for single command:

```bash
OPS_K8S_CONTEXT=production-cluster ops k8s pods list
```

---

### Kubeconfig Conflicts

**Symptoms**: Commands behave unexpectedly or switch clusters unintentionally

**Cause**:

- Multiple kubeconfig files are being merged
- KUBECONFIG environment variable has multiple paths
- ~/.kube/config and $KUBECONFIG both set with conflicts
- Context names are duplicated across files

**Solution**:

1. Check KUBECONFIG variable:

```bash
echo $KUBECONFIG
echo $KUBECONFIG | tr ':' '\n'  # View each file
```

1. Merge kubeconfigs properly:

```bash
# Backup current files
cp ~/.kube/config ~/.kube/config.backup

# Merge multiple kubeconfig files
KUBECONFIG=~/.kube/config:~/.kube/staging.config:~/.kube/production.config \
  kubectl config view > ~/.kube/config.merged
```

1. Check for duplicate context names:

```bash
grep "name:" ~/.kube/config ~/.kube/staging.config ~/.kube/production.config | grep -o 'name: [^[:space:]]*' | sort | uniq -d
```

1. Rename conflicting contexts:

```bash
# Rename context to avoid conflicts
kubectl config rename-context staging-cluster staging-old
kubectl config rename-context staging-cluster-v2 staging-cluster
```

1. Set single KUBECONFIG:

```bash
export KUBECONFIG=~/.kube/config
# Unset multiple
unset KUBECONFIG
```

1. Verify single kubeconfig is used:

```bash
echo $KUBECONFIG
ops k8s contexts
```

---

## Namespace Issues

### Namespace Not Found

**Symptoms**: "namespace not found" or "no resource found"

**Cause**:

- Namespace doesn't exist in cluster
- Namespace name is misspelled
- Namespace was deleted
- Wrong cluster selected (checking different cluster)

**Solution**:

1. List all namespaces:

```bash
ops k8s namespaces list
kubectl get namespaces
```

1. Check namespace exists:

```bash
ops k8s namespaces get production
ops k8s namespaces get production --output json
```

1. Create namespace if missing:

```bash
ops k8s namespaces create production -l env=production
kubectl create namespace production --dry-run=client -o yaml | kubectl apply -f -
```

1. Verify you're on correct cluster:

```bash
ops k8s status
ops k8s contexts
```

1. Check for typos:

```bash
# Find similar namespace names
ops k8s namespaces list | grep prod
ops k8s namespaces list | grep -i production
```

---

### No Resources in Namespace

**Symptoms**: Namespace exists but lists no resources (pods, deployments, etc.)

**Cause**:

- Namespace is empty
- Resources are in different namespace
- Resources haven't been deployed yet
- RBAC prevents viewing resources
- Selector is too restrictive

**Solution**:

1. Check what's in the namespace:

```bash
ops k8s pods list -n production
ops k8s deployments list -n production
ops k8s all-resources list -n production  # if available
```

1. Check all namespaces:

```bash
ops k8s pods list -A
ops k8s pods list --all-namespaces
```

1. Verify resources are deployed:

```bash
ops k8s deployments list -n production
ops k8s replicasets list -n production
```

1. Check with label selectors:

```bash
ops k8s pods list -n production -l app=myapp
ops k8s pods list -n production --field-selector status.phase=Running
```

1. Check RBAC permissions:

```bash
kubectl auth can-i list pods -n production
kubectl auth can-i get deployments -n production
```

1. Deploy resources:

```bash
ops k8s manifest apply -f my-app.yaml
kubectl apply -f deployment.yaml
```

---

### Default Namespace Confusion

**Symptoms**: Commands work in one namespace but not another, or "resource not found" in default namespace

**Cause**:

- Configuration has different default namespace than expected
- Forgot to specify namespace with `-n` flag
- Different context has different default namespace
- Resource is in different namespace

**Solution**:

1. Check configured default namespace:

```bash
cat ~/.config/ops/config.yaml | grep namespace
kubectl config view --minify | grep namespace
```

1. Check current context's default namespace:

```bash
kubectl config current-context
kubectl config view | grep -A3 "current-context:"
```

1. Specify namespace explicitly:

```bash
# Use -n flag
ops k8s pods list -n my-app
ops k8s pods get my-pod -n my-app

# Or search all namespaces
ops k8s pods list -A
```

1. Change default namespace:

```bash
# For kubectl
kubectl config set-context --current --namespace=production

# For ops (edit config)
cat > ~/.config/ops/config.yaml << 'EOF'
plugins:
  kubernetes:
    clusters:
      prod:
        context: "prod-cluster"
        namespace: "production"  # Set default
EOF
```

1. Override with environment variable:

```bash
OPS_K8S_NAMESPACE=production ops k8s pods list
```

---

## Ecosystem Tool Detection

### Helm Binary Not Found

**Symptoms**: "helm: command not found" or "Helm not available"

**Cause**:

- Helm is not installed
- Helm is not in PATH
- Wrong Helm version
- Shell needs reload after installation

**Solution**:

1. Check if Helm is installed:

```bash
which helm
helm version
```

1. Install Helm:

```bash
# macOS with Homebrew
brew install helm

# Linux with curl
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Windows with chocolatey
choco install kubernetes-helm

# From binary
wget https://get.helm.sh/helm-v3.12.0-linux-amd64.tar.gz
tar -zxvf helm-v3.12.0-linux-amd64.tar.gz
sudo mv linux-amd64/helm /usr/local/bin/
```

1. Verify installation:

```bash
helm version
helm repo list
helm search repo stable
```

1. Check Helm is in PATH:

```bash
echo $PATH
which helm
/usr/local/bin/helm version
```

1. Reload shell if recently installed:

```bash
exec $SHELL
helm version
```

1. Update Helm:

```bash
helm version
helm repo update
# Or reinstall newer version
```

---

### CRDs Missing or Not Available

**Symptoms**: "no matches for kind" or "resource not found" for ecosystem tools

**Cause**:

- Custom Resource Definitions (CRDs) are not installed
- Operator/controller is not running
- CRDs are in different cluster
- Incorrect API version

**Solution**:

1. Check if CRDs are installed:

```bash
kubectl get crds | grep argocd
kubectl get crds | grep kyverno
kubectl api-resources | grep -i certificate
```

1. Install missing CRDs:

```bash
# ArgoCD
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Kyverno
kubectl apply -f https://github.com/kyverno/kyverno/releases/download/v1.9.0/install.yaml

# Cert-Manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Flux
kubectl apply -f https://github.com/fluxcd/flux2/releases/download/v2.1.0/install.yaml
```

1. Verify installation:

```bash
ops k8s argocd applications list
ops k8s policies list
ops k8s certs certificates list
```

1. Check operators are running:

```bash
# ArgoCD
ops k8s pods list -n argocd

# Kyverno
ops k8s pods list -n kyverno

# Cert-Manager
ops k8s pods list -n cert-manager
```

1. Check API versions:

```bash
kubectl api-versions | grep -E "argoproj|kyverno|cert"
kubectl explain Application.argoproj.io
```

---

### Version Mismatch

**Symptoms**: "failed to parse", API version errors, or feature not available

**Cause**:

- Tool version doesn't match cluster Kubernetes version
- CRD schema changed in newer version
- Feature requires newer/older version
- Tool was upgraded without cluster upgrade

**Solution**:

1. Check versions:

```bash
# Kubernetes
kubectl version

# Tools
helm version
ops k8s helm version --client
argocd version
kyverno version
```

1. Check Kubernetes compatibility:

```bash
# For Helm charts
ops k8s helm search repo nginx
ops k8s helm info nginx --output yaml | grep appVersion

# For operators
kubectl describe crd applications.argoproj.io
```

1. Update tools to match cluster:

```bash
# Update Helm
helm repo update
helm repo upgrade

# Update ArgoCD
kubectl set image deployment/argocd-server \
  -n argocd \
  argocd-server=argoproj/argocd:latest

# Update other tools similarly
```

1. Downgrade if newer version not compatible:

```bash
# For Helm charts
ops k8s helm install my-release stable/nginx --version 13.0.0

# For binary tools, reinstall specific version
helm version  # Check current
# Download older version and reinstall
```

1. Check feature availability:

```bash
# Check if feature exists
kubectl api-resources | grep <resource>
kubectl explain <resource>.spec
```

---

## TUI Issues

### Terminal Doesn't Support Colors

**Symptoms**: TUI shows wrong colors, missing colors, or text is unreadable

**Cause**:

- Terminal doesn't support 256 colors
- TERM environment variable is set wrong
- Terminal emulator doesn't support colors
- SSH session has color limitations

**Solution**:

1. Check terminal color support:

```bash
echo $TERM
tput colors  # Should show 256 or higher
```

1. Set TERM to color-supporting value:

```bash
# For 256-color support
export TERM=xterm-256color
export TERM=screen-256color
export TERM=tmux-256color

# Test
ops k8s tui

# Make permanent
echo "export TERM=xterm-256color" >> ~/.bashrc
source ~/.bashrc
```

1. Update terminal emulator:

- iTerm2: Settings > Profiles > Terminal > Report terminal type
- GNOME Terminal: Edit > Preferences > Compatibility
- Windows Terminal: Settings > Appearance > Color scheme

1. Check SSH color support:

```bash
# On remote server
export TERM=xterm-256color
ops k8s tui

# Or force colors through SSH
ssh -o SendEnv=TERM your-server
```

1. Test colors:

```bash
# Simple color test
printf '\033[38;5;196mRed\033[0m\n'
printf '\033[38;5;46mGreen\033[0m\n'
printf '\033[38;5;21mBlue\033[0m\n'

# If colors show, terminal supports 256 colors
```

---

### TUI Rendering Issues

**Symptoms**: Garbled text, overlapping elements, or display corruption

**Cause**:

- Terminal window too small
- Terminal doesn't support Unicode
- Curses library incompatibility
- Python rendering issue

**Solution**:

1. Resize terminal window:

```bash
# Make sure terminal is at least 80x24
stty size
echo "Rows: $LINES, Columns: $COLUMNS"

# Resize terminal manually if too small
```

1. Check Unicode support:

```bash
echo $LANG
locale

# Set to UTF-8
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
```

1. Refresh TUI view:

```bash
# Inside TUI, press R to refresh
# Or restart TUI
ops k8s tui
```

1. Update Python and curses:

```bash
python --version
python -m curses.window

# Reinstall if needed
pip install --upgrade setuptools
pip install --upgrade pycurses
```

1. Check terminal capabilities:

```bash
# Show terminal info
infocmp
tput -S <<< $'clear\ncup 10 20\nsgr0'
```

---

### Navigation Doesn't Respond

**Symptoms**: Arrow keys don't work, Tab doesn't work, or keys seem unresponsive

**Cause**:

- Terminal in wrong input mode
- Scroll lock is enabled
- Keys are bound to different actions
- Terminal emulator issue

**Solution**:

1. Check input mode:

```bash
# Check stty settings
stty -a
stty sane  # Reset to sane defaults
```

1. Try different navigation:

```bash
# Inside TUI, try:
# - Arrow keys for navigation
# - [J]/[K] for vi-style movement
# - Tab for tab switching
# - Q to quit
```

1. Disable scroll lock:

```bash
# In terminal: press Scroll Lock key
# Check if indicator turns off
```

1. Restart TUI:

```bash
ops k8s tui
# Or kill and restart
pkill -f "ops k8s tui"
ops k8s tui
```

1. Try different terminal emulator:

```bash
# If current terminal doesn't work
# Try: Terminal, xterm, konsole, alacritty, iTerm2
```

---

## Resource Operations

### Create Fails with Invalid Configuration

**Symptoms**: "invalid value", "validation failed", or "schema validation error"

**Cause**:

- Resource manifest has invalid values
- Required fields are missing
- Field type is wrong (string vs integer)
- Values don't match regex pattern

**Solution**:

1. Validate manifest before applying:

```bash
ops k8s manifest validate -f deployment.yaml
kubectl apply -f deployment.yaml --dry-run=server -o yaml
```

1. Check required fields:

```bash
# Show what fields are required
kubectl explain deployment
kubectl explain deployment.spec
kubectl explain deployment.spec.template.spec.containers
```

1. Validate against schema:

```bash
# Check field types
kubectl explain pods.spec.containers.resources.limits
kubectl api-resources -o wide
```

1. Use example as template:

```bash
# Get working example
kubectl get deployment my-app -o yaml > deployment-example.yaml

# Use as base for new deployment
cp deployment-example.yaml my-new-deployment.yaml
vim my-new-deployment.yaml
```

1. Check specific field errors:

```bash
# Apply and show detailed error
kubectl apply -f deployment.yaml
# Look for field name in error message
# Fix that field

# Or use dry-run to preview
ops k8s manifest apply -f deployment.yaml --dry-run=server
```

---

### Delete Hangs or Doesn't Complete

**Symptoms**: Delete command hangs indefinitely or resource stays in "Terminating" state

**Cause**:

- Finalizers are preventing deletion
- Pod is stuck in termination grace period
- Persistent volumes have retain policy
- Webhook is blocking deletion

**Solution**:

1. Check resource status:

```bash
ops k8s pods describe my-pod -n my-app
kubectl get pod my-pod -o json | jq '.metadata.deletionTimestamp'
```

1. Check finalizers:

```bash
kubectl get pod my-pod -o json | jq '.metadata.finalizers'
```

1. Remove finalizers to force deletion:

```bash
# Remove specific finalizer
kubectl patch pod my-pod -p '{"metadata":{"finalizers":null}}'

# Or remove all
kubectl delete pod my-pod --grace-period=0 --force
```

1. Increase grace period:

```bash
# Default is 30 seconds
ops k8s pods delete my-pod -n my-app --grace-period=60
```

1. Force delete:

```bash
# Skip graceful termination
kubectl delete pod my-pod --grace-period=0 --force
ops k8s pods delete my-pod -n my-app --force
```

1. Check PersistentVolume reclaim:

```bash
# Check PV status
kubectl get pv
kubectl describe pv my-pv | grep ReclaimPolicy

# For Retain policy, manually delete PV after pod deletes
```

---

### Scale Timeout or Fails

**Symptoms**: Scale command times out, deployment doesn't scale, or reports error

**Cause**:

- Insufficient cluster resources
- Node resource limits reached
- Image can't be pulled
- Pod is in pending state

**Solution**:

1. Check node resources:

```bash
ops k8s nodes list
ops k8s top nodes
ops k8s top pods -n my-app
```

1. Check pod events:

```bash
ops k8s events list -n my-app --field-selector involvedObject.name=my-pod
kubectl describe pod my-pod -n my-app
```

1. Check resource requests:

```bash
kubectl get deployment my-app -o json | jq '.spec.template.spec.containers[].resources'
```

1. Reduce replica count and try:

```bash
ops k8s deployments scale my-app -n my-app --replicas=1
# Wait for pod to start

# Then scale up slowly
ops k8s deployments scale my-app -n my-app --replicas=2
```

1. Check image availability:

```bash
# Check pod for image pull errors
kubectl describe pod <pod-name> -n my-app | grep -A5 Events
```

1. Wait for resources:

```bash
# Monitor pod startup
watch kubectl get pods -n my-app
# Wait for Running state

# Then scale
ops k8s deployments scale my-app -n my-app --replicas=5
```

---

## Common Error Messages

| Error Message                                   | Cause                         | Solution             |
| ----------------------------------------------- | ----------------------------- | -------------------- |
| `connection refused`                            | Cluster API server not        | Verify cluster is    |
| `unable to connect to the                       | Connection dropped or timeout | Check cluster        |
| `the server has asked for the client to provide | Authentication not configured | Set up kubeconfig    |
| `error: resource type not found`                | Resource type doesn't exist   | Check resource name  |
| `forbidden: User "..."                          | Insufficient RBAC permissions | Check permissions    |
| `the namespace does                             | Namespace doesn't exist       | List namespaces      |
| `no matches for                                 | CRD not installed             | Install required     |
| `pending` pod status                            | Pod waiting for               | Check events with    |
| `ImagePullBackOff`                              | Can't pull                    | Verify image name    |
| `CrashLoopBackOff`                              | Container crashes             | Check logs with      |
| `OOMKilled`                                     | Pod ran out of                | Increase memory      |
| `evicted`                                       | Pod was evicted due to        | Check node resources |
| `x509: certificate                              | TLS certificate expired       | Update kubeconfig    |
| `i/o timeout`                                   | Request timed                 | Increase timeout     |
| `Too many requests`                             | Rate limited by               | Reduce request       |
| `invalid request`                               | Malformed API                 | Check manifest       |
| `not found`                                     | Resource doesn'               | Check resource name  |
| `already exists`                                | Resource alread               | Use update instead   |
| `invalid value`                                 | Field value doesn't           | Check field type     |
| `Deployment does not have minimum               | Not enough replicas ready     | Wait for pods to     |

---

## Diagnostic Commands

### Check Cluster Status

```bash
# Overall status
ops k8s status

# Detailed cluster info
ops k8s cluster-info

# All nodes
ops k8s nodes list

# Resource usage
ops k8s top nodes
ops k8s top pods -A

# Events across cluster
ops k8s events list -A

# Version info
kubectl version
```

### Check Authentication

```bash
# Current user/context
kubectl auth whoami
kubectl config current-context

# Available contexts
ops k8s contexts

# Check permissions
kubectl auth can-i get pods -A
kubectl auth can-i list deployments -n production
kubectl auth can-i create statefulsets --list
```

### Check Connectivity

```bash
# Test cluster reachability
ops k8s status

# Check API server directly
kubectl cluster-info

# DNS resolution
nslookup api.example.com
dig api.example.com

# Network connectivity
curl -k https://api.example.com:6443/api/v1
```

### Debug Deployments

```bash
# List and status
ops k8s deployments list -n my-app
ops k8s deployments get my-app -n my-app

# Check pods
ops k8s pods list -n my-app

# View events
ops k8s events list -n my-app

# Check logs
ops k8s logs <pod-name> -n my-app

# Describe for details
kubectl describe deployment my-app -n my-app
```

### Export Cluster State

```bash
# Get all resources
kubectl get all -A -o yaml > cluster-state.yaml

# Diagnostic dump
kubectl cluster-info dump --output-directory=./cluster-dump

# Export as JSON
ops k8s pods list -A --output json > pods-export.json
```

---

## Environment Variable Conflicts

### OPS_K8S_CONTEXT Override

**Problem**: Environment variable overrides configuration file

**Diagnostic**:

```bash
echo $OPS_K8S_CONTEXT
echo $OPS_K8S_NAMESPACE
echo $OPS_K8S_KUBECONFIG
```

**Solution**:

```bash
# Unset override
unset OPS_K8S_CONTEXT
unset OPS_K8S_NAMESPACE

# Verify correct context
ops k8s contexts
ops k8s status
```

### Multiple KUBECONFIG Files

**Problem**: KUBECONFIG set to multiple files causes conflicts

**Diagnostic**:

```bash
echo $KUBECONFIG
echo $KUBECONFIG | tr ':' '\n'  # View each file
grep "current-context:" ~/.kube/config
```

**Solution**:

```bash
# Use single kubeconfig
unset KUBECONFIG
export KUBECONFIG=~/.kube/config
ops k8s status

# Or set correct order
export KUBECONFIG=~/.kube/prod.config:~/.kube/staging.config
ops k8s contexts
```

### Environment Precedence

**Problem**: Understanding which setting takes precedence

**Precedence Order** (highest to lowest):

1. Command-line flags: `ops k8s pods list -n production`
2. Environment variables: `OPS_K8S_NAMESPACE=production`
3. Configuration file: `~/.config/ops/config.yaml`
4. Defaults: timeout: 300, retry_attempts: 3

**Solution**:

```bash
# Check which setting is active
echo "ENV: $OPS_K8S_TIMEOUT"
cat ~/.config/ops/config.yaml | grep timeout
ops k8s status  # Shows which context is active

# Test override
ops k8s pods list -n production  # Uses -n flag first
OPS_K8S_NAMESPACE=staging ops k8s pods list  # Uses env var
# (Config file used if both above unset)
```

---

## Performance and Timeouts

### Commands Running Slowly

**Symptoms**: Commands take too long to complete

**Cause**:

- Large cluster with many resources
- Slow network to API server
- API server is under load
- Command is listing too many resources

**Solution**:

1. Use namespace filtering:

```bash
# Instead of all namespaces
ops k8s pods list -A

# Use specific namespace
ops k8s pods list -n production
```

1. Use label selectors:

```bash
# Instead of all pods
ops k8s pods list -n production

# Filter by labels
ops k8s pods list -n production -l app=myapp
ops k8s pods list -n production -l environment=prod
```

1. Use field selectors:

```bash
# Filter by field
ops k8s pods list -n production --field-selector status.phase=Running
```

1. Check cluster performance:

```bash
ops k8s top nodes
ops k8s top pods -n kube-system
```

1. Increase timeout for slow commands:

```bash
OPS_K8S_TIMEOUT=60 ops k8s pods list -A
```

---

### Manifest Apply Is Slow

**Symptoms**: Apply command takes long time to complete

**Cause**:

- Large manifests with many resources
- Rolling updates taking time
- Waiting for pod readiness
- API server processing time

**Solution**:

1. Use dry-run first:

```bash
# Validate without applying
ops k8s manifest apply -f large-manifest.yaml --dry-run=server
```

1. Apply in smaller batches:

```bash
# Instead of all at once
ops k8s manifest apply -f all.yaml

# Apply separately
ops k8s manifest apply -f namespace.yaml
sleep 10
ops k8s manifest apply -f deployments.yaml
```

1. Skip waiting for readiness:

```bash
# Don't wait for deployment to be ready
kubectl apply -f deployment.yaml
# Check status separately
ops k8s deployments get my-app -n my-app
```

1. Monitor progress:

```bash
# Watch rolling update progress
watch ops k8s deployments get my-app -n my-app
```

---

## RBAC and Permissions

### Service Account Has No Permissions

**Symptoms**: Service account can't perform operations, permission denied errors

**Cause**:

- Service account has no roles assigned
- Role doesn't have required verbs
- RoleBinding is missing or in wrong namespace

**Solution**:

1. Check service account permissions:

```bash
kubectl auth can-i get pods --as=system:serviceaccount:default:my-sa
kubectl auth can-i list deployments --as=system:serviceaccount:default:my-sa
```

1. Create role with required permissions:

```bash
cat > role.yaml << 'EOF'
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
  namespace: default
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list"]
EOF

kubectl apply -f role.yaml
```

1. Create RoleBinding to grant permissions:

```bash
cat > rolebinding.yaml << 'EOF'
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods-binding
  namespace: default
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: pod-reader
subjects:
- kind: ServiceAccount
  name: my-sa
  namespace: default
EOF

kubectl apply -f rolebinding.yaml
```

1. Verify permissions now work:

```bash
kubectl auth can-i get pods --as=system:serviceaccount:default:my-sa
```

---

## See Also

- [Examples](./examples.md) - Working examples for common scenarios
- [Commands Reference](./commands/) - Detailed command documentation
- [Kubernetes Plugin Index](./index.md) - Complete plugin documentation
- [Kubernetes Official Docs](https://kubernetes.io/docs/) - Official documentation
