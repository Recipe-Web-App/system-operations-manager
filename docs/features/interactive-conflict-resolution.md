# Interactive Conflict Resolution

Terminal-based UI (TUI) for resolving configuration conflicts during Kong Gateway
and Konnect synchronization operations.

## Overview

When syncing configuration between Kong Gateway and Konnect control plane, entities
may have different values on each side (drift). The interactive conflict resolution
feature provides a terminal UI to:

- **View Conflicts**: See all entities with configuration differences
- **Compare Side-by-Side**: View source and target values with diff highlighting
- **Resolve Individually**: Choose how to handle each conflict
- **Batch Operations**: Apply the same resolution to multiple conflicts
- **Merge Changes**: Combine fields from both sides or edit manually

## Quick Start

```bash
# Push with interactive conflict resolution
ops kong sync push --interactive

# Pull with interactive conflict resolution
ops kong sync pull --with-drift --interactive

# Dry-run to preview conflicts before interactive resolution
ops kong sync push --dry-run
ops kong sync push --interactive
```

## Resolution Actions

When resolving a conflict, you can choose from these actions:

| Action          | Description                                      | When to Use                             |
| --------------- | ------------------------------------------------ | --------------------------------------- |
| **Keep Source** | Use the source system's configuration            | Source has the correct/newer values     |
| **Keep Target** | Keep the target system's configuration unchanged | Target values should not be overwritten |
| **Merge**       | Combine fields from both sides                   | Different fields changed on each side   |
| **Skip**        | Don't sync this entity                           | Need to investigate further             |

### Push vs Pull Direction

The meaning of "source" and "target" depends on the sync direction:

| Direction | Source  | Target  | "Keep Source" Effect     |
| --------- | ------- | ------- | ------------------------ |
| **Push**  | Gateway | Konnect | Gateway values → Konnect |
| **Pull**  | Konnect | Gateway | Konnect values → Gateway |

## TUI Navigation

### Conflict List Screen

The main screen shows all detected conflicts grouped by entity type.

**Keyboard Shortcuts:**

| Key      | Action                             |
| -------- | ---------------------------------- |
| `↑`/`k`  | Move up                            |
| `↓`/`j`  | Move down                          |
| `Enter`  | View conflict details              |
| `s`      | Apply "Keep Source" to all pending |
| `t`      | Apply "Keep Target" to all pending |
| `m`      | Apply "Auto-merge" to all pending  |
| `a`      | Apply changes (go to summary)      |
| `Escape` | Cancel and exit                    |
| `?`      | Show help                          |

**Example Display:**

```text
┌─ Conflict Resolution ────────────────────────────────────┐
│                                                          │
│  Entity Type     Name              Status     Action     │
│  ─────────────────────────────────────────────────────   │
│  services        payment-api       Pending    -          │
│  services        auth-service      Resolved   keep_source│
│  routes          payment-route     Pending    -          │
│  plugins         rate-limiting     Pending    -          │
│                                                          │
│  4 conflicts (2 pending, 2 resolved)                     │
│                                                          │
│  [s] Source All  [t] Target All  [a] Apply  [Esc] Cancel │
└──────────────────────────────────────────────────────────┘
```

### Conflict Detail Screen

View the full diff for a single conflict with resolution options.

**Keyboard Shortcuts:**

| Key      | Action                                 |
| -------- | -------------------------------------- |
| `1`      | Keep Source                            |
| `2`      | Keep Target                            |
| `3`      | Skip this conflict                     |
| `4`      | Merge (if available)                   |
| `d`      | Toggle diff mode (side-by-side/inline) |
| `Escape` | Back to list                           |

**Example Display:**

```text
┌─ Conflict: services/payment-api ─────────────────────────┐
│                                                          │
│  Source (Gateway)          │  Target (Konnect)           │
│  ─────────────────────────────────────────────────────   │
│  host: gw.example.com      │  host: kn.example.com       │
│  port: 8080                │  port: 80                   │
│  protocol: http            │  protocol: http             │
│  retries: 5                │  retries: 3                 │
│                                                          │
│  Drift fields: host, port, retries                       │
│                                                          │
│  [1] Keep Source  [2] Keep Target  [3] Skip  [4] Merge   │
└──────────────────────────────────────────────────────────┘
```

### Merge Preview Screen

When merge is available (non-overlapping changes), preview the merged result.

**Keyboard Shortcuts:**

| Key      | Action          |
| -------- | --------------- |
| `c`      | Confirm merge   |
| `e`      | Edit in $EDITOR |
| `Escape` | Cancel merge    |

## Merge Capabilities

### Automatic Merge

When source and target have modified different fields, automatic merge is possible:

```yaml
# Source (Gateway)
host: gateway.example.com
port: 8080          # Modified on Gateway
protocol: https

# Target (Konnect)
host: gateway.example.com
port: 80
protocol: http      # Modified on Konnect

# Auto-merged result
host: gateway.example.com
port: 8080          # From Gateway
protocol: http      # From Konnect
```

### Manual Merge ($EDITOR)

For complex conflicts or when you need full control, use the editor option:

1. Press `e` on the Merge Preview Screen
2. Edit the YAML in your configured `$EDITOR`
3. Save and close to apply the merge
4. Comments at the top explain the conflict

**Editor Template:**

```yaml
# Conflict Resolution - services/payment-api
# Direction: push (Gateway -> Konnect)
#
# Instructions:
# - Edit the values below to create your merged configuration
# - Lines starting with # are ignored
# - Save and close to apply, or delete all content to cancel
#
# Conflicting fields: host, port

host: gateway.example.com
port: 8080
protocol: https
retries: 5
```

## Summary Screen

Before applying changes, review all resolutions:

```text
┌─ Resolution Summary ─────────────────────────────────────┐
│                                                          │
│  Ready to apply 4 resolutions:                           │
│                                                          │
│  Entity                  Action                          │
│  ─────────────────────────────────────────────────────   │
│  services/payment-api    keep_source (sync to Konnect)   │
│  services/auth-service   keep_target (no change)         │
│  routes/payment-route    merge (combined values)         │
│  plugins/rate-limiting   skip (no action)                │
│                                                          │
│  Will sync: 2 entities                                   │
│  Will skip: 2 entities                                   │
│                                                          │
│  [Enter] Confirm and Apply    [Escape] Go Back           │
└──────────────────────────────────────────────────────────┘
```

## Batch Operations

Apply the same resolution to multiple conflicts at once:

### From Conflict List

- Press `s` to apply "Keep Source" to all **pending** conflicts
- Press `t` to apply "Keep Target" to all **pending** conflicts

> **Note:** Batch operations only affect conflicts that haven't been resolved yet.
> Previously resolved conflicts are not modified.

### Workflow Example

```bash
# 1. Start interactive sync
ops kong sync push --interactive

# 2. In TUI: Review the first conflict in detail (Enter)
# 3. Decide this type needs Gateway values, press 's' (Keep Source)
# 4. Press Escape to return to list
# 5. Use 's' to apply Keep Source to remaining pending conflicts
# 6. Press 'a' to review summary
# 7. Press Enter to apply all resolutions
```

## Audit Integration

All resolutions are recorded in the sync audit trail:

```bash
# View sync history with resolution details
ops kong sync history

# Example audit entry
ops kong sync history show <sync-id>
```

**Audit Entry Fields:**

| Field               | Description                                               |
| ------------------- | --------------------------------------------------------- |
| `resolution_action` | The chosen action (keep_source, keep_target, merge, skip) |
| `before_state`      | Entity state before resolution                            |
| `after_state`       | Entity state after resolution (if synced)                 |
| `resolved_by`       | User who made the resolution                              |
| `resolved_at`       | Timestamp of resolution                                   |

## Skip Conflicts Mode

As an alternative to interactive resolution, use `--skip-conflicts` to automatically
skip all conflicting entities and only sync clean ones:

```bash
# Push only non-conflicting entities
ops kong sync push --skip-conflicts --force

# Pull only non-conflicting entities
ops kong sync pull --with-drift --skip-conflicts --force
```

This is useful for:

- CI/CD pipelines where manual intervention isn't possible
- Syncing known-good entities while investigating conflicts separately
- Partial sync when you know some entities have intentional drift

## Configuration

### Editor Configuration

Set your preferred editor for manual merges:

```bash
# Use vim
export EDITOR=vim

# Use VS Code
export EDITOR="code --wait"

# Use nano
export EDITOR=nano
```

### TUI Theme

The TUI uses colors that work with most terminal themes. For best results:

- Use a terminal with 256-color support
- Dark themes generally provide better contrast for diffs

## Troubleshooting

### TUI Not Launching

If the TUI doesn't launch when using `--interactive`:

1. **No conflicts detected**: If there's no drift, the sync proceeds without TUI
2. **Terminal not supported**: Ensure you're running in a TTY (not piped output)
3. **Konnect not configured**: Interactive mode requires valid Konnect credentials

### Merge Not Available

Merge is only available when:

- Source and target have modified different fields
- The entity has an "original state" for 3-way comparison

When merge isn't available, you'll see "Manual merge required" and can use the
`$EDITOR` option.

### Editor Doesn't Open

If pressing `e` doesn't open your editor:

1. Check that `$EDITOR` environment variable is set
2. Ensure the editor command is in your `$PATH`
3. For GUI editors, include the "wait" flag (e.g., `code --wait`, `subl -w`)

## Related Documentation

- [Kong Plugin Documentation](../plugins/kong.md) - Full sync command reference
- [History and Rollback](./history-rollback.md) - Sync history and rollback features
- [Dry Run Mode](./dry-run-mode.md) - Preview changes before applying
