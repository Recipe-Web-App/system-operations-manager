# Kong Gateway Clean Reinstall & Entity Deployment Runbook

Guide for removing HttpRoute resources from Konnect, performing a full Kong gateway
teardown in minikube, deploying fresh, and pushing service registry entities to both
data and control planes.

---

## Phase 0: Pre-Flight Assessment

Establish the current state before making any changes.

```bash
# Check deployment health
ops kong deploy status

# Find all HttpRoute CRDs in the cluster
kubectl get httproutes --all-namespaces -o wide

# List services and routes across both planes
ops kong services list
ops kong routes list

# Check what's in the service registry (this is what we'll deploy later)
ops kong registry list

# Verify Konnect connectivity
ops kong konnect status

# Confirm the Konnect TLS secret exists (must be preserved)
kubectl get secret konnect-client-tls -n kong
```

**Record the HttpRoute names and namespaces** — you'll need them in Phase 1.

---

## Phase 1: Delete HttpRoute Kubernetes Resources

> **Why do this first?** KIC (Kong Ingress Controller) manages the sync of
> HttpRoutes to Konnect. If we uninstall Kong first, KIC is gone and the
> Konnect entities become orphaned with no controller to clean them up.

### Step 1.1 — Delete all HttpRoutes

```bash
# Delete all HttpRoutes in the relevant namespace
kubectl delete httproutes --all -n <namespace>
```

### Step 1.2 — Wait for KIC to reconcile

KIC needs time to process the deletions and propagate them to both the Gateway Admin API and Konnect.

```bash
sleep 15
```

### Step 1.3 — Verify removal from Gateway

```bash
ops kong routes list --source gateway
ops kong services list --source gateway
```

The HttpRoute-derived routes and services should no longer appear. If they do, wait another 30 seconds and check again.

### Step 1.4 — Verify removal from Konnect

```bash
ops kong routes list --source konnect
ops kong services list --source konnect
```

### Step 1.5 — Manual cleanup (if Konnect entities persist)

If KIC didn't clean up the Konnect entities automatically:

```bash
# IMPORTANT: Delete routes BEFORE services (Kong returns 409 Conflict otherwise)
ops kong routes delete <route-name-or-id> --force
ops kong services delete <service-name-or-id> --force
```

### Checkpoint

Both `ops kong routes list` and `ops kong services list` show no HttpRoute-derived entities in either source.

---

## Phase 2: Full Kong Gateway Uninstall

### Step 2.1 — Uninstall Kong and delete PostgreSQL PVC

```bash
ops kong deploy uninstall --force --delete-pvc
```

This will:

- Run `helm uninstall kong -n kong`
- Delete the PostgreSQL PVC for a clean database on reinstall
- **Preserve** the `konnect-client-tls` secret (it was created by `konnect setup`,
  not by `deploy install`, so the uninstall command does not touch it)

### Step 2.2 — Clean up RBAC patch resources

```bash
kubectl delete clusterrole kong-controller-endpoints --ignore-not-found
kubectl delete clusterrolebinding kong-controller-endpoints --ignore-not-found
```

### Step 2.3 — Verify cleanup

```bash
# Should show no running resources
kubectl get all -n kong

# Should show no PVCs
kubectl get pvc -n kong

# konnect-client-tls should still be here
kubectl get secrets -n kong
```

### Checkpoint — Uninstall Verified

No running resources in the kong namespace. `konnect-client-tls` secret still exists.

---

## Phase 3: Deploy a Fresh Kong Gateway

### Step 3.1 — Verify prerequisites

```bash
# Secrets file for PostgreSQL
ls -la config/.env.kong.secrets

# Helm values file
ls -la k8s/gateway/kong-values.yaml

# Konnect TLS secret still in K8s
kubectl get secret konnect-client-tls -n kong
```

> If `konnect-client-tls` is missing (e.g., namespace was fully deleted), recreate it:
>
> ```bash
> ops kong konnect setup --control-plane <name-or-id> --force
> ```

### Step 3.2 — Install Kong

```bash
ops kong deploy install
```

This will:

1. Add/update the Kong Helm repository
2. Create the `kong` namespace (if not exists)
3. Create `kong-postgres-secret` from `config/.env.kong.secrets`
4. Apply `k8s/gateway/postgres.yaml` (PostgreSQL StatefulSet)
5. Wait for PostgreSQL to be ready
6. Install Kong CRDs from `kong/ingress` chart
7. Run `helm install kong kong/ingress -n kong -f k8s/gateway/kong-values.yaml`

### Step 3.3 — Wait for stabilization

```bash
sleep 30
```

### Step 3.4 — Verify deployment

```bash
ops kong deploy status
```

Expected: Status = Running, PostgreSQL = Ready, Gateway = Ready, Controller = Ready.

### Step 3.5 — Set up Admin API access

```bash
kubectl port-forward svc/kong-gateway-admin -n kong 8001:8001 &
```

### Step 3.6 — Verify gateway and Konnect connectivity

```bash
# Gateway node status
ops kong status

# Konnect connection
ops kong konnect status

# Baseline sync state (should be clean/empty)
ops kong sync status
```

### Checkpoint — Gateway Running

`ops kong deploy status` shows RUNNING. `ops kong konnect status` shows
Connection OK. `ops kong sync status` shows a clean baseline.

---

## Phase 4: Deploy Service Registry Entities

### Step 4.1 — Review registry contents

```bash
ops kong registry list
```

### Step 4.2 — Preview deployment (dry run)

```bash
ops kong registry deploy --dry-run
```

Review the output to confirm what will be created in both Gateway and Konnect.

### Step 4.3 — Deploy to both planes

```bash
ops kong registry deploy
```

This creates/updates services (and their routes, if OpenAPI specs are configured) in
both the Gateway Admin API and Konnect control plane.

### Step 4.4 — Verify entities in both planes

```bash
ops kong services list --source gateway
ops kong services list --source konnect
ops kong routes list --source gateway
ops kong routes list --source konnect
```

### Step 4.5 — Check sync status

```bash
ops kong sync status
```

Should show zero drift between Gateway and Konnect.

### Step 4.6 — Fix sync gaps (if needed)

If Gateway deploy succeeded but Konnect failed:

```bash
ops kong sync push --dry-run    # Preview what would be pushed
ops kong sync push --force      # Execute the push
```

### Checkpoint — Entities Deployed

`ops kong services list` and `ops kong routes list` show identical entities in
both planes. `ops kong sync status` shows zero drift.

---

## Phase 5: End-to-End Verification

### Step 5.1 — Test proxy traffic

```bash
# Port-forward the proxy service
kubectl port-forward svc/kong-gateway-proxy -n kong 8000:80 &

# Test a route (adjust path to match your registry routes)
curl -v http://localhost:8000/<your-route-path>
```

### Step 5.2 — Verify in Konnect UI

Log into [cloud.konghq.com](https://cloud.konghq.com) and verify:

- Data plane node is connected and reporting
- All services and routes from the registry are visible
- No orphaned HttpRoute-derived entities remain

### Step 5.3 — Final sync check

```bash
ops kong sync status
```

---

## Troubleshooting

### Phase 1 — HttpRoutes won't delete from Konnect

- Wait up to 60 seconds for KIC reconciliation
- If KIC isn't running, manually delete via `ops kong routes delete` then `ops kong services delete` (routes first!)

### Phase 2 — Uninstall stuck

- Try `helm uninstall kong -n kong` directly
- For stuck resources: `kubectl delete <resource> --force --grace-period=0`
- Nuclear option: `kubectl delete namespace kong` (warning: deletes `konnect-client-tls` too)

### Phase 3 — Install failures

- **PostgreSQL not ready**: Check PVC binding with `kubectl get pvc -n kong`, check logs with `kubectl logs -n kong kong-postgres-0`
- **Gateway CrashLoopBackOff**: Usually a DB migration issue — `kubectl logs -n kong -l app.kubernetes.io/component=gateway`
- **Konnect TLS failure**: Verify `konnect-client-tls` has valid `tls.crt` and `tls.key` data
- Retry with: `ops kong deploy install --force`

### Phase 4 — Registry deploy partial failure

- `ops kong registry deploy` is idempotent — safe to re-run
- Deploy individual services: `ops kong registry deploy --service <name>`
- Push gateway state to Konnect: `ops kong sync push --force`

---

## Quick Reference — Full Command Sequence

```bash
# ---- Phase 0: Pre-flight ----
ops kong deploy status
kubectl get httproutes --all-namespaces -o wide
ops kong services list
ops kong routes list
ops kong registry list
ops kong konnect status
kubectl get secret konnect-client-tls -n kong

# ---- Phase 1: Delete HttpRoutes ----
kubectl delete httproutes --all -n <namespace>
sleep 15
ops kong routes list --source gateway
ops kong services list --source gateway
ops kong routes list --source konnect
ops kong services list --source konnect

# ---- Phase 2: Clean uninstall ----
ops kong deploy uninstall --force --delete-pvc
kubectl delete clusterrole kong-controller-endpoints --ignore-not-found
kubectl delete clusterrolebinding kong-controller-endpoints --ignore-not-found
kubectl get all -n kong
kubectl get secrets -n kong

# ---- Phase 3: Fresh install ----
ops kong deploy install
sleep 30
ops kong deploy status
kubectl port-forward svc/kong-gateway-admin -n kong 8001:8001 &
ops kong status
ops kong konnect status
ops kong sync status

# ---- Phase 4: Deploy entities ----
ops kong registry list
ops kong registry deploy --dry-run
ops kong registry deploy
ops kong services list
ops kong routes list
ops kong sync status

# ---- Phase 5: Verify ----
kubectl port-forward svc/kong-gateway-proxy -n kong 8000:80 &
curl -v http://localhost:8000/<your-route-path>
ops kong sync status
```
