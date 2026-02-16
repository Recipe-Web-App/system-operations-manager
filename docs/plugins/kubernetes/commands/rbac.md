# Kubernetes Plugin > Commands > RBAC

[< Back to Index](../index.md) | [Commands](./) | [Ecosystem](../ecosystem/) | [TUI](../tui.md) | [Examples](../examples.md)

---

## Table of Contents

- [Overview](#overview)
- [Common Options](#common-options)
- [Service Accounts](#service-accounts)
  - [List Service Accounts](#list-service-accounts)
  - [Get Service Account](#get-service-account)
  - [Create Service Account](#create-service-account)
  - [Delete Service Account](#delete-service-account)
- [Roles](#roles)
  - [List Roles](#list-roles)
  - [Get Role](#get-role)
  - [Create Role](#create-role)
  - [Delete Role](#delete-role)
- [Cluster Roles](#cluster-roles)
  - [List Cluster Roles](#list-cluster-roles)
  - [Get Cluster Role](#get-cluster-role)
  - [Create Cluster Role](#create-cluster-role)
  - [Delete Cluster Role](#delete-cluster-role)
- [Role Bindings](#role-bindings)
  - [List Role Bindings](#list-role-bindings)
  - [Get Role Binding](#get-role-binding)
  - [Create Role Binding](#create-role-binding)
  - [Delete Role Binding](#delete-role-binding)
- [Cluster Role Bindings](#cluster-role-bindings)
  - [List Cluster Role Bindings](#list-cluster-role-bindings)
  - [Get Cluster Role Binding](#get-cluster-role-binding)
  - [Create Cluster Role Binding](#create-cluster-role-binding)
  - [Delete Cluster Role Binding](#delete-cluster-role-binding)
- [Troubleshooting](#troubleshooting)
- [See Also](#see-also)

---

## Overview

Role-Based Access Control (RBAC) commands manage permissions in Kubernetes. These commands organize into five resource
types:

- **Service Accounts** - Identities for processes running in pods
- **Roles** - Sets of permissions within a namespace
- **Cluster Roles** - Sets of permissions across the entire cluster
- **Role Bindings** - Grant Role permissions to subjects within a namespace
- **Cluster Role Bindings** - Grant Cluster Role permissions to subjects across the cluster

RBAC follows the principle of least privilege: assign only necessary permissions. Each binding connects a subject
(ServiceAccount, User, Group) to a role with specific permissions.

---

## Common Options

Options available across most RBAC commands:

| Option             | Short | Type   | Default             | Description                      |
| ------------------ | ----- | ------ | ------------------- | -------------------------------- |
| `--namespace`      | `-n`  | string | config or 'default' | Kubernetes namespace             |
| `--all-namespaces` | `-A`  | flag   | false               | List across all namespaces       |
| `--selector`       | `-l`  | string | none                | Filter by labels                 |
| `--output`         | `-o`  | string | table               | Output format: table, json, yaml |
| `--force`          | `-f`  | flag   | false               | Skip confirmation prompts        |
| `--label`          | `-l`  | string | none                | Add labels to created resources  |

---

## Service Accounts

Service Accounts are identities for processes running in pods. Every pod runs as a Service Account, defaulting to the
"default" Service Account in its namespace.

### List Service Accounts

List all Service Accounts in a namespace or across all namespaces.

```bash
ops k8s service-accounts list
ops k8s service-accounts list -n production
ops k8s service-accounts list -A
ops k8s service-accounts list -l app=database
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
Service Accounts
┌─────────────────────┬────────────┬─────────┬─────┐
│ Name                │ Namespace  │ Secrets │ Age │
├─────────────────────┼────────────┼─────────┼─────┤
│ default             │ default    │ 1       │ 30d │
│ app-service-account │ default    │ 1       │ 15d │
│ db-admin            │ production │ 1       │ 10d │
│ ci-runner           │ production │ 1       │ 5d  │
└─────────────────────┴────────────┴─────────┴─────┘
```

**Notes:**

- Every namespace has a "default" ServiceAccount automatically created
- Each ServiceAccount can have associated secrets for API access
- Use `--all-namespaces` to audit service accounts cluster-wide
- Labels help organize and categorize ServiceAccounts

---

### Get Service Account

Retrieve detailed information about a specific Service Account.

```bash
ops k8s service-accounts get default
ops k8s service-accounts get app-service-account -n production
ops k8s service-accounts get app-service-account -o yaml
```

**Options:**

| Option        | Short | Type   | Default             | Description                      |
| ------------- | ----- | ------ | ------------------- | -------------------------------- |
| `--namespace` | `-n`  | string | config or 'default' | Kubernetes namespace             |
| `--output`    | `-o`  | string | table               | Output format: table, json, yaml |

**Example Output:**

```text
ServiceAccount: app-service-account
┌──────────────────┬──────────────────────────────┐
│ Field            │ Value                        │
├──────────────────┼──────────────────────────────┤
│ Name             │ app-service-account          │
│ Namespace        │ default                      │
│ Secrets          │ 1                            │
│ Secret Name      │ app-service-account-token... │
│ Auto-Mount Token │ True                         │
│ Age              │ 15 days                      │
│ Created          │ 2024-02-01T12:30:00Z         │
│ Labels           │ app=myapp, tier=backend      │
└──────────────────┴──────────────────────────────┘
```

**Notes:**

- Shows associated secrets (API tokens for authentication)
- Auto-mount token controls if token is available in pods
- Use to verify ServiceAccount configuration and bindings
- Check for associated tokens if pods need API access

---

### Create Service Account

Create a new Service Account for pods to use.

```bash
ops k8s service-accounts create my-sa
ops k8s service-accounts create app-admin -n production
ops k8s service-accounts create my-sa --label app=web --label tier=frontend
```

**Options:**

| Option        | Short | Type   | Default             | Description                      |
| ------------- | ----- | ------ | ------------------- | -------------------------------- |
| `--namespace` | `-n`  | string | config or 'default' | Kubernetes namespace             |
| `--label`     | `-l`  | string | none                | Label (key=value, repeatable)    |
| `--output`    | `-o`  | string | table               | Output format: table, json, yaml |

**Examples:**

Create basic ServiceAccount:

```bash
ops k8s service-accounts create api-client
```

Create with labels for organization:

```bash
ops k8s service-accounts create db-operator \
  --label app=database \
  --label tier=backend \
  --label role=operator
```

Create in specific namespace:

```bash
ops k8s service-accounts create job-runner \
  -n production \
  --label type=job
```

**Example Output:**

```text
Created ServiceAccount: my-sa
┌───────────┬────────────────────────┐
│ Field     │ Value                  │
├───────────┼────────────────────────┤
│ Name      │ my-sa                  │
│ Namespace │ default                │
│ Status    │ Created                │
│ Secrets   │ 1                      │
│ Labels    │ app=web, tier=frontend │
│ Created   │ 2024-02-16T12:00:00Z   │
└───────────┴────────────────────────┘
```

**Notes:**

- ServiceAccount token is automatically created
- Token is used for pod-to-API authentication
- ServiceAccounts must be created before binding to roles
- Labels improve organization and querying

---

### Delete Service Account

Delete a Service Account from the cluster.

```bash
ops k8s service-accounts delete my-sa
ops k8s service-accounts delete my-sa -n production
ops k8s service-accounts delete my-sa -f
```

**Options:**

| Option        | Short | Type   | Default             | Description              |
| ------------- | ----- | ------ | ------------------- | ------------------------ |
| `--namespace` | `-n`  | string | config or 'default' | Kubernetes namespace     |
| `--force`     | `-f`  | flag   | false               | Skip confirmation prompt |

**Example Output:**

```text
Are you sure you want to delete service account 'my-sa' in namespace 'default'? [y/N]: y
ServiceAccount 'my-sa' deleted
```

**Notes:**

- Requires confirmation unless `--force` is used
- Cannot delete if pods are currently using this ServiceAccount
- Deletion removes associated tokens
- Consider impact on pods and role bindings before deletion

---

## Roles

Roles define a set of permissions within a namespace. They contain rules that specify allowed API operations on
resources.

### List Roles

List all Roles in a namespace.

```bash
ops k8s roles list
ops k8s roles list -n kube-system
ops k8s roles list -l app=auth
```

**Options:**

| Option        | Short | Type   | Default             | Description                      |
| ------------- | ----- | ------ | ------------------- | -------------------------------- |
| `--namespace` | `-n`  | string | config or 'default' | Kubernetes namespace             |
| `--selector`  | `-l`  | string | none                | Filter by labels                 |
| `--output`    | `-o`  | string | table               | Output format: table, json, yaml |

**Example Output:**

```text
Roles
┌─────────────────┬────────────┬───────┬─────┐
│ Name            │ Namespace  │ Rules │ Age │
├─────────────────┼────────────┼───────┼─────┤
│ pod-reader      │ default    │ 1     │ 20d │
│ pod-writer      │ default    │ 2     │ 15d │
│ configmap-admin │ production │ 1     │ 10d │
│ secret-reader   │ production │ 1     │ 5d  │
└─────────────────┴────────────┴───────┴─────┘
```

**Notes:**

- Namespace-scoped: list only roles in specified namespace
- Each role can contain multiple rules with different permissions
- Rules count shows number of permission rules in each role
- Use labels to organize roles by application or purpose

---

### Get Role

Retrieve detailed information about a specific Role.

```bash
ops k8s roles get pod-reader
ops k8s roles get pod-reader -n production
ops k8s roles get pod-reader -o yaml
```

**Options:**

| Option        | Short | Type   | Default             | Description                      |
| ------------- | ----- | ------ | ------------------- | -------------------------------- |
| `--namespace` | `-n`  | string | config or 'default' | Kubernetes namespace             |
| `--output`    | `-o`  | string | table               | Output format: table, json, yaml |

**Example Output:**

```text
Role: pod-reader
┌─────────────────────────┬──────────────────────┐
│ Field                   │ Value                │
├─────────────────────────┼──────────────────────┤
│ Name                    │ pod-reader           │
│ Namespace               │ default              │
│ Rules                   │ 1                    │
│ Age                     │ 20 days              │
│ Created                 │ 2024-01-27T10:15:00Z │
│ Labels                  │ app=monitoring       │
│ Rules Details:          │                      │
│ - API Groups: [""]      │                      │
│ - Resources: ["pods"]   │                      │
│ - Verbs: ["get","list"] │                      │
└─────────────────────────┴──────────────────────┘
```

**Notes:**

- Shows all permission rules defined in the role
- Rules specify API groups, resources, and allowed verbs (actions)
- Use to understand what permissions are granted
- Useful for auditing and compliance verification

---

### Create Role

Create a new Role with permission rules.

```bash
ops k8s roles create pod-reader \
  --rule '{"verbs":["get","list"],"api_groups":[""],"resources":["pods"]}'
```

**Options:**

| Option        | Short | Type   | Default             | Description                      |
| ------------- | ----- | ------ | ------------------- | -------------------------------- |
| `--namespace` | `-n`  | string | config or 'default' | Kubernetes namespace             |
| `--rule`      |       | string | none                | Policy rule as JSON (repeatable) |
| `--label`     | `-l`  | string | none                | Label (key=value, repeatable)    |
| `--output`    | `-o`  | string | table               | Output format: table, json, yaml |

**Rule Format:**

Rules are specified as JSON with this structure:

```json
{
  "verbs": ["get", "list", "watch"],
  "api_groups": ["", "apps"],
  "resources": ["pods", "deployments"]
}
```

Common verbs: `get`, `list`, `watch`, `create`, `update`, `patch`, `delete`, `deletecollection`

API groups: `""` (core), `"apps"` (apps), `"batch"` (batch), `"rbac.authorization.k8s.io"`, etc.

**Examples:**

Create role to read pods:

```bash
ops k8s roles create pod-reader \
  --rule '{"verbs":["get","list"],"api_groups":[""],"resources":["pods"]}'
```

Create role with multiple permissions:

```bash
ops k8s roles create configmap-admin \
  --rule '{"verbs":["get","list","watch"],"api_groups":[""],"resources":["configmaps"]}' \
  --rule '{"verbs":["create","update","patch","delete"],"api_groups":[""],"resources":["configmaps"]}'
```

Create role with labels:

```bash
ops k8s roles create secret-reader \
  --rule '{"verbs":["get","list"],"api_groups":[""],"resources":["secrets"]}' \
  --label app=myapp \
  --label env=production
```

Create in specific namespace:

```bash
ops k8s roles create deployment-manager \
  -n production \
  --rule '{"verbs":["get","list","watch","create","update","patch","delete"],"api_groups":["apps"],"resources":["deployments"]}'
```

**Example Output:**

```text
Created Role: pod-reader
┌───────────┬──────────────────────┐
│ Field     │ Value                │
├───────────┼──────────────────────┤
│ Name      │ pod-reader           │
│ Namespace │ default              │
│ Status    │ Created              │
│ Rules     │ 1                    │
│ Created   │ 2024-02-16T12:30:00Z │
└───────────┴──────────────────────┘
```

**Notes:**

- Rules must be valid JSON format
- Multiple rules can be added by specifying `--rule` multiple times
- Think about least privilege when defining rules
- Test rules with RBAC simulation before production use

---

### Delete Role

Delete a Role from the cluster.

```bash
ops k8s roles delete pod-reader
ops k8s roles delete pod-reader -n production
ops k8s roles delete pod-reader -f
```

**Options:**

| Option        | Short | Type   | Default             | Description              |
| ------------- | ----- | ------ | ------------------- | ------------------------ |
| `--namespace` | `-n`  | string | config or 'default' | Kubernetes namespace     |
| `--force`     | `-f`  | flag   | false               | Skip confirmation prompt |

**Example Output:**

```text
Are you sure you want to delete role 'pod-reader' in namespace 'default'? [y/N]: y
Role 'pod-reader' deleted
```

**Notes:**

- Requires confirmation unless `--force` is used
- Deleting a role does not delete associated RoleBindings
- Subjects bound to this role lose permissions after deletion
- Consider impact on applications before deletion

---

## Cluster Roles

Cluster Roles are similar to Roles but apply cluster-wide, not limited to a namespace. Use for cluster-scoped resources
like nodes and persistent volumes.

### List Cluster Roles

List all Cluster Roles in the cluster.

```bash
ops k8s cluster-roles list
ops k8s cluster-roles list -l app=system
ops k8s cluster-roles list -o yaml
```

**Options:**

| Option       | Short | Type   | Default | Description                      |
| ------------ | ----- | ------ | ------- | -------------------------------- |
| `--selector` | `-l`  | string | none    | Filter by labels                 |
| `--output`   | `-o`  | string | table   | Output format: table, json, yaml |

**Example Output:**

```text
Cluster Roles
┌──────────────────────┬───────┬─────┐
│ Name                 │ Rules │ Age │
├──────────────────────┼───────┼─────┤
│ cluster-admin        │ 1     │ 30d │
│ admin                │ 1     │ 30d │
│ edit                 │ 1     │ 30d │
│ view                 │ 1     │ 30d │
│ node-reader          │ 2     │ 15d │
│ persistent-vol-admin │ 1     │ 10d │
└──────────────────────┴───────┴─────┘
```

**Notes:**

- Cluster-scoped: not restricted by namespace
- Includes system-created cluster roles (cluster-admin, edit, view, etc.)
- Filter by labels to find custom cluster roles
- Use for system-wide permissions and cluster operations

---

### Get Cluster Role

Retrieve detailed information about a specific Cluster Role.

```bash
ops k8s cluster-roles get cluster-admin
ops k8s cluster-roles get node-reader
ops k8s cluster-roles get node-reader -o json
```

**Options:**

| Option     | Short | Type   | Default | Description                      |
| ---------- | ----- | ------ | ------- | -------------------------------- |
| `--output` | `-o`  | string | table   | Output format: table, json, yaml |

**Example Output:**

```text
ClusterRole: cluster-admin
┌─────────────────────┬─────────────────────────────┐
│ Field               │ Value                       │
├─────────────────────┼─────────────────────────────┤
│ Name                │ cluster-admin               │
│ Rules               │ 1                           │
│ Age                 │ 30 days                     │
│ Created             │ 2024-01-17T08:00:00Z        │
│ Labels              │ kubernetes.io/bootstrapping │
│ Rules Details:      │                             │
│ - API Groups: ["*"] │                             │
│ - Resources: ["*"]  │                             │
│ - Verbs: ["*"]      │                             │
└─────────────────────┴─────────────────────────────┘
```

**Notes:**

- Shows all permission rules defined in the cluster role
- `cluster-admin` grants all permissions on all resources
- Use to understand cluster-level permissions
- Useful for auditing and compliance

---

### Create Cluster Role

Create a new Cluster Role with permission rules.

```bash
ops k8s cluster-roles create node-reader \
  --rule '{"verbs":["get","list"],"api_groups":[""],"resources":["nodes"]}'
```

**Options:**

| Option     | Short | Type   | Default | Description                      |
| ---------- | ----- | ------ | ------- | -------------------------------- |
| `--rule`   |       | string | none    | Policy rule as JSON (repeatable) |
| `--label`  | `-l`  | string | none    | Label (key=value, repeatable)    |
| `--output` | `-o`  | string | table   | Output format: table, json, yaml |

**Rule Format:**

Rules are specified as JSON:

```json
{
  "verbs": ["get", "list", "watch"],
  "api_groups": [""],
  "resources": ["nodes"]
}
```

**Examples:**

Create cluster role for node management:

```bash
ops k8s cluster-roles create node-manager \
  --rule '{"verbs":["get","list","watch"],"api_groups":[""],"resources":["nodes"]}' \
  --rule '{"verbs":["patch","update"],"api_groups":[""],"resources":["nodes/status"]}'
```

Create cluster role for persistent volume management:

```bash
ops k8s cluster-roles create persistent-vol-admin \
  --rule '{"verbs":["get","list","watch","create","update","delete"],"api_groups":[""],"resources":["persistentvolumes"]}'
```

Create with labels:

```bash
ops k8s cluster-roles create storage-admin \
  --rule '{"verbs":["*"],"api_groups":[""],"resources":["persistentvolumes","persistentvolumeclaims"]}' \
  --label app=storage \
  --label tier=system
```

**Example Output:**

```text
Created ClusterRole: node-reader
┌─────────┬──────────────────────┐
│ Field   │ Value                │
├─────────┼──────────────────────┤
│ Name    │ node-reader          │
│ Status  │ Created              │
│ Rules   │ 1                    │
│ Created │ 2024-02-16T13:00:00Z │
└─────────┴──────────────────────┘
```

**Notes:**

- Cluster-scoped rules apply across all namespaces
- Use for system-wide and cluster operations
- Be cautious with broad permissions (_:_)
- Test rules before production deployment

---

### Delete Cluster Role

Delete a Cluster Role from the cluster.

```bash
ops k8s cluster-roles delete node-reader
ops k8s cluster-roles delete node-reader -f
```

**Options:**

| Option    | Short | Type | Default | Description              |
| --------- | ----- | ---- | ------- | ------------------------ |
| `--force` | `-f`  | flag | false   | Skip confirmation prompt |

**Example Output:**

```text
Are you sure you want to delete cluster role 'node-reader'? [y/N]: y
ClusterRole 'node-reader' deleted
```

**Notes:**

- Requires confirmation unless `--force` is used
- Deleting a cluster role does not delete associated ClusterRoleBindings
- System cluster roles (cluster-admin, edit, view) should not be deleted
- Consider impact before deletion

---

## Role Bindings

Role Bindings grant permissions defined in a Role to subjects within a namespace. Subjects can be ServiceAccounts,
Users, or Groups.

### List Role Bindings

List all Role Bindings in a namespace.

```bash
ops k8s role-bindings list
ops k8s role-bindings list -n production
ops k8s role-bindings list -l app=auth
```

**Options:**

| Option        | Short | Type   | Default             | Description                      |
| ------------- | ----- | ------ | ------------------- | -------------------------------- |
| `--namespace` | `-n`  | string | config or 'default' | Kubernetes namespace             |
| `--selector`  | `-l`  | string | none                | Filter by labels                 |
| `--output`    | `-o`  | string | table               | Output format: table, json, yaml |

**Example Output:**

```text
Role Bindings
┌───────────────┬────────────┬───────────┬──────────────┬──────────┬─────┐
│ Name          │ Namespace  │ Role Kind │ Role Name    │ Subjects │ Age │
├───────────────┼────────────┼───────────┼──────────────┼──────────┼─────┤
│ read-pods     │ default    │ Role      │ pod-reader   │ 1        │ 15d │
│ admin-binding │ default    │ Role      │ admin        │ 2        │ 10d │
│ db-access     │ production │ Role      │ db-admin     │ 1        │ 5d  │
│ app-config    │ production │ Role      │ configmap... │ 3        │ 2d  │
└───────────────┴────────────┴───────────┴──────────────┴──────────┴─────┘
```

**Notes:**

- Namespace-scoped: list only bindings in specified namespace
- Shows role references and number of subjects
- Use labels to organize bindings by purpose

---

### Get Role Binding

Retrieve detailed information about a specific Role Binding.

```bash
ops k8s role-bindings get read-pods
ops k8s role-bindings get read-pods -n production
ops k8s role-bindings get read-pods -o yaml
```

**Options:**

| Option        | Short | Type   | Default             | Description                      |
| ------------- | ----- | ------ | ------------------- | -------------------------------- |
| `--namespace` | `-n`  | string | config or 'default' | Kubernetes namespace             |
| `--output`    | `-o`  | string | table               | Output format: table, json, yaml |

**Example Output:**

```text
RoleBinding: read-pods
┌────────────────┬──────────────────────┐
│ Field          │ Value                │
├────────────────┼──────────────────────┤
│ Name           │ read-pods            │
│ Namespace      │ default              │
│ Role Reference │ Role/pod-reader      │
│ Subjects       │ 1                    │
│ Subject Type   │ ServiceAccount       │
│ Subject Name   │ app-reader           │
│ Age            │ 15 days              │
│ Created        │ 2024-02-01T14:20:00Z │
│ Labels         │ app=monitoring       │
└────────────────┴──────────────────────┘
```

**Notes:**

- Shows role reference and all subjects with this binding
- Subjects can be ServiceAccounts, Users, or Groups
- Use to verify permissions for specific subjects

---

### Create Role Binding

Create a Role Binding to grant a Role to one or more subjects.

```bash
ops k8s role-bindings create read-pods \
  --role-ref '{"kind":"Role","name":"pod-reader","api_group":"rbac.authorization.k8s.io"}' \
  --subject '{"kind":"ServiceAccount","name":"app-reader"}'
```

**Options:**

| Option        | Short | Type        | Default             | Description                      |
| ------------- | ----- | ----------- | ------------------- | -------------------------------- |
| `--namespace` | `-n`  | string      | config or 'default' | Kubernetes namespace             |
| `--role-ref`  |       | JSON string | required            | Role reference as JSON           |
| `--subject`   |       | JSON string | none                | Subject as JSON (repeatable)     |
| `--label`     | `-l`  | string      | none                | Label (key=value, repeatable)    |
| `--output`    | `-o`  | string      | table               | Output format: table, json, yaml |

**JSON Format:**

Role reference:

```json
{
  "kind": "Role",
  "name": "pod-reader",
  "api_group": "rbac.authorization.k8s.io"
}
```

Subject:

```json
{
  "kind": "ServiceAccount",
  "name": "app-reader",
  "namespace": "default"
}
```

Subject kinds: `ServiceAccount`, `User`, `Group`

**Examples:**

Bind role to ServiceAccount:

```bash
ops k8s role-bindings create pod-reader-binding \
  --role-ref '{"kind":"Role","name":"pod-reader","api_group":"rbac.authorization.k8s.io"}' \
  --subject '{"kind":"ServiceAccount","name":"app-reader","namespace":"default"}'
```

Bind role to multiple subjects:

```bash
ops k8s role-bindings create config-admin-binding \
  --role-ref '{"kind":"Role","name":"configmap-admin","api_group":"rbac.authorization.k8s.io"}' \
  --subject '{"kind":"ServiceAccount","name":"admin-sa","namespace":"default"}' \
  --subject '{"kind":"User","name":"admin@example.com"}'
```

Bind with labels:

```bash
ops k8s role-bindings create db-access-binding \
  --role-ref '{"kind":"Role","name":"db-admin","api_group":"rbac.authorization.k8s.io"}' \
  --subject '{"kind":"ServiceAccount","name":"db-operator"}' \
  --label app=database \
  --label env=production
```

Bind in specific namespace:

```bash
ops k8s role-bindings create production-admin \
  -n production \
  --role-ref '{"kind":"Role","name":"admin","api_group":"rbac.authorization.k8s.io"}' \
  --subject '{"kind":"ServiceAccount","name":"prod-admin"}'
```

**Example Output:**

```text
Created RoleBinding: read-pods
┌───────────┬──────────────────────┐
│ Field     │ Value                │
├───────────┼──────────────────────┤
│ Name      │ read-pods            │
│ Namespace │ default              │
│ Status    │ Created              │
│ Role      │ pod-reader           │
│ Subjects  │ 1                    │
│ Created   │ 2024-02-16T13:30:00Z │
└───────────┴──────────────────────┘
```

**Notes:**

- Role reference must specify kind, name, and api_group
- Multiple subjects can be added with repeating `--subject` options
- Subjects must exist before binding (create ServiceAccounts first)
- Verify bindings grant appropriate permissions

---

### Delete Role Binding

Delete a Role Binding from the cluster.

```bash
ops k8s role-bindings delete read-pods
ops k8s role-bindings delete read-pods -n production
ops k8s role-bindings delete read-pods -f
```

**Options:**

| Option        | Short | Type   | Default             | Description              |
| ------------- | ----- | ------ | ------------------- | ------------------------ |
| `--namespace` | `-n`  | string | config or 'default' | Kubernetes namespace     |
| `--force`     | `-f`  | flag   | false               | Skip confirmation prompt |

**Example Output:**

```text
Are you sure you want to delete role binding 'read-pods' in namespace 'default'? [y/N]: y
RoleBinding 'read-pods' deleted
```

**Notes:**

- Requires confirmation unless `--force` is used
- Deleting binding revokes permissions from subjects
- Role itself is not deleted
- Consider impact on applications and users

---

## Cluster Role Bindings

Cluster Role Bindings grant permissions defined in a Cluster Role to subjects cluster-wide. Similar to Role Bindings but
for cluster-scoped roles.

### List Cluster Role Bindings

List all Cluster Role Bindings in the cluster.

```bash
ops k8s cluster-role-bindings list
ops k8s cluster-role-bindings list -l app=system
ops k8s cluster-role-bindings list -o yaml
```

**Options:**

| Option       | Short | Type   | Default | Description                      |
| ------------ | ----- | ------ | ------- | -------------------------------- |
| `--selector` | `-l`  | string | none    | Filter by labels                 |
| `--output`   | `-o`  | string | table   | Output format: table, json, yaml |

**Example Output:**

```text
Cluster Role Bindings
┌──────────────────────────┬─────────────┬───────────────┬──────────┬─────┐
│ Name                     │ Role Kind   │ Role Name     │ Subjects │ Age │
├──────────────────────────┼─────────────┼───────────────┼──────────┼─────┤
│ cluster-admin            │ ClusterRole │ cluster-admin │ 1        │ 30d │
│ system:kube-apiserver    │ ClusterRole │ system:master │ 1        │ 30d │
│ node-manager-binding     │ ClusterRole │ node-reader   │ 2        │ 15d │
│ persistent-vol-admin-... │ ClusterRole │ persistent... │ 1        │ 10d │
└──────────────────────────┴─────────────┴───────────────┴──────────┴─────┘
```

**Notes:**

- Cluster-scoped: not restricted by namespace
- Includes system-created bindings for Kubernetes components
- Filter by labels to find custom cluster role bindings

---

### Get Cluster Role Binding

Retrieve detailed information about a specific Cluster Role Binding.

```bash
ops k8s cluster-role-bindings get cluster-admin-binding
ops k8s cluster-role-bindings get node-manager-binding
ops k8s cluster-role-bindings get node-manager-binding -o json
```

**Options:**

| Option     | Short | Type   | Default | Description                      |
| ---------- | ----- | ------ | ------- | -------------------------------- |
| `--output` | `-o`  | string | table   | Output format: table, json, yaml |

**Example Output:**

```text
ClusterRoleBinding: cluster-admin
┌────────────────────────┬───────────────────────────┐
│ Field                  │ Value                     │
├────────────────────────┼───────────────────────────┤
│ Name                   │ cluster-admin             │
│ Cluster Role Reference │ ClusterRole/cluster-admin │
│ Subjects               │ 1                         │
│ Subject Type           │ ServiceAccount            │
│ Subject Name           │ admin                     │
│ Subject Namespace      │ kube-system               │
│ Age                    │ 30 days                   │
│ Created                │ 2024-01-17T08:00:00Z      │
└────────────────────────┴───────────────────────────┘
```

**Notes:**

- Shows cluster role reference and all subjects
- Subjects can span multiple namespaces
- Use to understand cluster-level permissions

---

### Create Cluster Role Binding

Create a Cluster Role Binding to grant a Cluster Role to subjects cluster-wide.

```bash
ops k8s cluster-role-bindings create admin-binding \
  --role-ref '{"kind":"ClusterRole","name":"cluster-admin","api_group":"rbac.authorization.k8s.io"}' \
  --subject '{"kind":"User","name":"admin"}'
```

**Options:**

| Option       | Short | Type        | Default  | Description                      |
| ------------ | ----- | ----------- | -------- | -------------------------------- |
| `--role-ref` |       | JSON string | required | Role reference as JSON           |
| `--subject`  |       | JSON string | none     | Subject as JSON (repeatable)     |
| `--label`    | `-l`  | string      | none     | Label (key=value, repeatable)    |
| `--output`   | `-o`  | string      | table    | Output format: table, json, yaml |

**JSON Format:**

Cluster role reference:

```json
{
  "kind": "ClusterRole",
  "name": "cluster-admin",
  "api_group": "rbac.authorization.k8s.io"
}
```

Subject:

```json
{
  "kind": "User",
  "name": "admin@example.com"
}
```

Subject kinds: `ServiceAccount`, `User`, `Group`

**Examples:**

Bind cluster role to user:

```bash
ops k8s cluster-role-bindings create user-admin \
  --role-ref '{"kind":"ClusterRole","name":"cluster-admin","api_group":"rbac.authorization.k8s.io"}' \
  --subject '{"kind":"User","name":"admin@example.com"}'
```

Bind cluster role to group:

```bash
ops k8s cluster-role-bindings create ops-team \
  --role-ref '{"kind":"ClusterRole","name":"edit","api_group":"rbac.authorization.k8s.io"}' \
  --subject '{"kind":"Group","name":"ops-team@example.com"}'
```

Bind cluster role to multiple subjects:

```bash
ops k8s cluster-role-bindings create system-admins \
  --role-ref '{"kind":"ClusterRole","name":"cluster-admin","api_group":"rbac.authorization.k8s.io"}' \
  --subject '{"kind":"User","name":"alice@example.com"}' \
  --subject '{"kind":"User","name":"bob@example.com"}'
```

Bind with labels:

```bash
ops k8s cluster-role-bindings create monitoring-access \
  --role-ref '{"kind":"ClusterRole","name":"view","api_group":"rbac.authorization.k8s.io"}' \
  --subject '{"kind":"ServiceAccount","name":"monitoring","namespace":"monitoring"}' \
  --label app=monitoring \
  --label role=viewer
```

**Example Output:**

```text
Created ClusterRoleBinding: admin-binding
┌─────────────┬──────────────────────┐
│ Field       │ Value                │
├─────────────┼──────────────────────┤
│ Name        │ admin-binding        │
│ Status      │ Created              │
│ ClusterRole │ cluster-admin        │
│ Subjects    │ 1                    │
│ Created     │ 2024-02-16T14:00:00Z │
└─────────────┴──────────────────────┘
```

**Notes:**

- Cluster role reference must specify kind, name, and api_group
- Multiple subjects can be added with repeating `--subject` options
- Applies permissions across all namespaces
- Be cautious with broad cluster-level permissions

---

### Delete Cluster Role Binding

Delete a Cluster Role Binding from the cluster.

```bash
ops k8s cluster-role-bindings delete admin-binding
ops k8s cluster-role-bindings delete admin-binding -f
```

**Options:**

| Option    | Short | Type | Default | Description              |
| --------- | ----- | ---- | ------- | ------------------------ |
| `--force` | `-f`  | flag | false   | Skip confirmation prompt |

**Example Output:**

```text
Are you sure you want to delete cluster role binding 'admin-binding'? [y/N]: y
ClusterRoleBinding 'admin-binding' deleted
```

**Notes:**

- Requires confirmation unless `--force` is used
- Deleting binding revokes cluster-wide permissions
- Cluster role itself is not deleted
- Consider impact on system components and users

---

## Troubleshooting

| Issue                           | Solution                                                                        |
| ------------------------------- | ------------------------------------------------------------------------------- |
| "cannot list service accounts"  | Check RBAC permissions. Verify kubeconfig credentials. Try                      |
| "role not found"                | Verify namespace with `-n` flag. Roles are                                      |
| "cannot create role binding"    | Verify ServiceAccount exists. Check role reference is                           |
| "subjects have no permissions"  | Verify RoleBinding or ClusterRoleBinding is created. Check role permissions.    |
| "JSON parsing error for rule"   | Ensure JSON is properly formatted. Escape quotes correctly.                     |
| "cannot bind non-existent role" | Create the role first before creating bindings. Verify role                     |
| "ServiceAccount token missing"  | Token auto-created with ServiceAccount. Check if auto-mount is disabled. Create |
| "Default ServiceAccount issues" | Default SA in each namespace. Don't delete unless necessary. Use                |
| "Cluster admin access denied"   | User may not have cluster-admin role. Check ClusterRoleBindings. Try            |
| "Role permission too broad"     | Review rule permissions. Remove unnecessary API groups. Follow least            |

---

## See Also

- [Configuration & Storage Commands](./configuration-storage.md) - Manage secrets and configurations with RBAC
- [Jobs Commands](./jobs.md) - Run jobs with specific service accounts
- [Kubernetes Plugin Index](../index.md) - Complete plugin documentation
- [Examples](../examples.md) - Common RBAC patterns and use cases
- [Ecosystem](../ecosystem/) - Related Kubernetes tools
- [TUI Interface](../tui.md) - Terminal UI for visualizing RBAC resources
