# Kubernetes Plugin > Commands > Streaming

[< Back to Index](../index.md) | [Commands](./) | [Ecosystem](../ecosystem/) | [TUI](../tui.md) | [Examples](../examples.md)

---

## Table of Contents

1. [Overview](#overview)
2. [Common Options](#common-options)
3. [Logs Command](#logs-command)
4. [Exec Command](#exec-command)
5. [Port-Forward Command](#port-forward-command)
6. [Example Workflows](#example-workflows)
7. [Troubleshooting](#troubleshooting)
8. [See Also](#see-also)

---

## Overview

The streaming command group provides real-time interaction with Kubernetes pods and services. These commands enable you
to view pod logs, execute commands inside containers, and forward local ports to pods or services for development and
debugging.

Key capabilities:

- **Logs**: View, stream, and filter pod logs with multiple output options
- **Exec**: Execute commands inside running containers with interactive TTY support
- **Port-Forward**: Tunnel local ports to pod or service ports for development and debugging
- **Real-time Streaming**: Follow logs and interactive sessions as they happen
- **Container Selection**: Target specific containers within multi-container pods
- **History Access**: View logs from previous container restarts

---

## Common Options

Options shared across streaming commands:

| Option        | Short | Type   | Default                     | Description                                |
| ------------- | ----- | ------ | --------------------------- | ------------------------------------------ |
| `--namespace` | `-n`  | string | config default or 'default' | Kubernetes namespace containing the target |

**Important**: The namespace option is used to locate the target pod or service. If not specified, the default namespace
from your kubeconfig context is used.

---

## Logs Command

### `ops k8s logs`

Retrieve and stream pod logs in real-time.

The logs command provides flexible log retrieval with options for filtering by container, following live logs, setting
time ranges, and more. Perfect for monitoring application behavior and debugging issues.

**Syntax:**

```bash
ops k8s logs <pod> [OPTIONS]
```

**Arguments:**

| Argument | Required | Type   | Description                           |
| -------- | -------- | ------ | ------------------------------------- |
| `pod`    | Yes      | string | Name of the pod to retrieve logs from |

**Options:**

| Option         | Short | Type    | Default         | Description                                                |
| -------------- | ----- | ------- | --------------- | ---------------------------------------------------------- |
| `--namespace`  | `-n`  | string  | config default  | Kubernetes namespace                                       |
| `--container`  | `-c`  | string  | first container | Specific container name within a                           |
| `--follow`     | `-f`  | boolean | false           | Stream logs in real-time                                   |
| `--tail`       |       | integer | all lines       | Number of most                                             |
| `--previous`   | `-p`  | boolean | false           | Show logs from the previous container instance (useful for |
| `--timestamps` |       | boolean | false           | Include timestamps                                         |
| `--since`      |       | string  |                 | Show logs since a relative time duration (e.g.,            |

**Duration Formats:**

The `--since` option accepts duration strings in the following formats:

- `30s` - 30 seconds ago
- `5m` - 5 minutes ago
- `2h` - 2 hours ago
- `1h30m` - 1 hour and 30 minutes ago
- `1h30m15s` - 1 hour, 30 minutes, and 15 seconds ago

**Behavior:**

1. Connects to the Kubernetes cluster and locates the specified pod
2. If `--container` is not specified, uses the first container in the pod
3. Retrieves logs based on the specified options (tail, since, previous)
4. If `--follow` is specified, streams new log lines in real-time
5. Timestamps can be added to each line with `--timestamps`
6. Ctrl+C stops log streaming without error

**Examples:**

Get the last 100 lines of logs from a pod:

```bash
ops k8s logs my-pod
```

Stream logs in real-time from a specific container:

```bash
ops k8s logs my-pod -f -c web-server
```

Show logs with timestamps from the last hour:

```bash
ops k8s logs my-pod --since 1h --timestamps
```

Get logs from the previous container instance (useful after a crash):

```bash
ops k8s logs my-pod --previous
```

Get last 50 lines and follow new logs:

```bash
ops k8s logs my-pod --tail 50 --follow
```

Show logs from a specific namespace with timestamps:

```bash
ops k8s logs my-pod -n production --timestamps
```

Combine multiple options for detailed troubleshooting:

```bash
ops k8s logs my-pod -f --container sidecar --timestamps --since 30m
```

**Example Output (static logs):**

```text
2026-02-16T10:45:23Z Starting application server...
2026-02-16T10:45:24Z Loading configuration from ConfigMap
2026-02-16T10:45:25Z Initializing database connection pool
2026-02-16T10:45:26Z Application ready on port 8080
2026-02-16T10:45:27Z Received request: GET /health
```

**Example Output (streaming with --follow):**

```text
2026-02-16T10:45:23Z Starting application server...
2026-02-16T10:45:24Z Loading configuration from ConfigMap
2026-02-16T10:45:25Z Initializing database connection pool
2026-02-16T10:45:26Z Application ready on port 8080
^C
Log streaming stopped.
```

**Notes:**

- Requires the pod to be in a running or completed state
- Log availability depends on container logging configuration and disk space
- For multi-container pods, you must specify `--container` or get logs from the first container
- Previous logs (`--previous`) only available if previous container completed or crashed
- Very large log outputs may be truncated by the console
- Press Ctrl+C to exit log streaming without errors

---

## Exec Command

### `ops k8s exec`

Execute a command inside a running pod container.

The exec command allows you to run arbitrary commands within a container for debugging, configuration checks, or
maintenance tasks. Supports both interactive TTY sessions and non-interactive command execution.

**Syntax:**

```bash
ops k8s exec <pod> [OPTIONS] [-- COMMAND]
```

**Arguments:**

| Argument  | Required | Type   | Description                                                                      |
| --------- | -------- | ------ | -------------------------------------------------------------------------------- |
| `pod`     | Yes      | string | Name of the pod to execute the                                                   |
| `COMMAND` | No       | string | Command and arguments to execute (after `--`). If omitted, starts an interactive |

**Options:**

| Option        | Short | Type    | Default         | Description                                               |
| ------------- | ----- | ------- | --------------- | --------------------------------------------------------- |
| `--namespace` | `-n`  | string  | config default  | Kubernetes namespace                                      |
| `--container` | `-c`  | string  | first container | Specific container name                                   |
| `--stdin`     | `-i`  | boolean | false           | Pass stdin to the container                               |
| `--tty`       | `-t`  | boolean | false           | Allocate a TTY for the session (enables terminal features |

**Command Specification:**

- Use `--` to separate exec options from the command to execute
- Without a command, starts an interactive shell
- The `-it` flags (stdin + tty) provide a full interactive terminal session
- Only `-i` allows input but is non-interactive (for piping data)
- Only `-t` allocates a TTY but may not provide stdin

**Behavior:**

1. Connects to the Kubernetes cluster and locates the specified pod
2. If `--container` is not specified, uses the first container
3. If `-it` flags are set, enters interactive TTY mode:
   - Terminal is set to raw mode for full control
   - Arrow keys, tab completion, and Ctrl+C work as expected
   - Session terminated by user exit command or Ctrl+C
4. If command is specified:
   - Executes the command and captures output
   - Returns the command's exit code
5. Output is printed to stdout/stderr in real-time

**Examples:**

Start an interactive shell in a pod:

```bash
ops k8s exec my-pod -it
```

Execute a specific command and exit:

```bash
ops k8s exec my-pod -- ls -la /app
```

Run a command in a specific container:

```bash
ops k8s exec my-pod -c sidecar -- cat /etc/hosts
```

Interactive bash session with explicit container:

```bash
ops k8s exec my-pod -c web -it -- /bin/bash
```

Execute a shell command with pipes and redirects:

```bash
ops k8s exec my-pod -- sh -c "ps aux | grep nginx"
```

Check environment variables in a container:

```bash
ops k8s exec my-pod -- env | grep DATABASE
```

Test database connectivity from within a pod:

```bash
ops k8s exec my-app-pod -- curl -v http://postgres:5432
```

Interactive debugging session in a specific namespace:

```bash
ops k8s exec my-pod -n production -it -- /bin/bash
```

**Example Output (non-interactive command):**

```text
total 48
drwxr-xr-x  5 root root 4096 Feb 16 10:45 .
drwxr-xr-x 18 root root 4096 Feb 16 10:30 ..
-rw-r--r--  1 root root  220 Feb 16  2026 .bashrc
-rw-r--r--  1 root root  256 Feb 16  2026 .profile
drwxr-xr-x  3 root root 4096 Feb 16 10:45 app
drwxr-xr-x  2 root root 4096 Feb 16 10:30 bin
```

**Example Output (interactive session):**

```text
# Interactive session starts
root@my-pod:/app# ls -la
total 48
drwxr-xr-x  5 root root 4096 Feb 16 10:45 .
-rw-r--r--  1 root root  256 Feb 16  2026 app.py
# ... more output
root@my-pod:/app# ps aux
USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
root         1  0.0  0.1  12345  6789 ?        Ss   10:45   0:00 python app.py
root       123  0.0  0.0  12345  4567 ?        R+   10:50   0:00 ps aux
root@my-pod:/app# exit
exit
Interactive session interrupted by user.
```

**Notes:**

- Interactive sessions (`-it`) only work on Unix/Linux terminals with termios support
- Windows users should use the `-i` flag and manually manage input/output
- The container must have a shell available (`/bin/bash`, `/bin/sh`, etc.) for interactive sessions
- Non-interactive commands execute within the container's working directory unless specified
- Environment variables set in the Dockerfile/manifest are available in exec sessions
- Ctrl+C in interactive mode is forwarded to the container; press it twice to force exit
- The command's exit code is returned as the exec command's exit code

---

## Port-Forward Command

### `ops k8s port-forward`

Forward local ports to a Kubernetes pod or service.

The port-forward command establishes a tunnel from your local machine to a pod or service port, enabling direct access
for development, debugging, and testing without exposing the service externally.

**Syntax:**

```bash
ops k8s port-forward <target> <port-mappings>... [OPTIONS]
```

**Arguments:**

| Argument        | Required | Type   | Description                                                             |
| --------------- | -------- | ------ | ----------------------------------------------------------------------- |
| `target`        | Yes      | string | Target pod or service: `pod/<name>`, `svc/<name>`, `service/<name>`, or |
| `port-mappings` | Yes      | string | Port mapping(s) in format `[local:]remote` (e.g., `8080:80`, `3000`,    |

**Port Mapping Format:**

- `port` - Forward local port to the same remote port
- `local:remote` - Forward local port to different remote port
- Multiple mappings can be specified as separate arguments

**Options:**

| Option        | Short | Type   | Default        | Description                                                    |
| ------------- | ----- | ------ | -------------- | -------------------------------------------------------------- |
| `--namespace` | `-n`  | string | config default | Kubernetes namespace                                           |
| `--address`   |       | string | 127.0.0.1      | Local address to bind to (127.0.0.1 for local machine, 0.0.0.0 |

**Target Format:**

- `pod/my-app` - Forward to specific pod
- `svc/my-service` - Forward to service (automatically resolves to one of its pods)
- `service/my-service` - Same as `svc/` (alternative syntax)
- `my-pod` - Shorthand for `pod/my-pod`

**Behavior:**

1. Parses and validates the target and port mappings
2. If target is a service, resolves it to one of the service's backing pods
3. Establishes port-forward connection to the Kubernetes API server
4. Creates local TCP listeners on the specified local ports
5. Forwards all traffic from local listeners to the remote pod ports
6. Prints listening status for each port mapping
7. Continues forwarding until interrupted with Ctrl+C
8. Gracefully closes all connections when stopped

**Examples:**

Forward local port 8080 to pod port 80:

```bash
ops k8s port-forward my-app 8080:80
```

Forward to a service (resolves to a pod automatically):

```bash
ops k8s port-forward svc/my-service 8080:80
```

Multiple port mappings to the same pod:

```bash
ops k8s port-forward my-app 8000:5000 9000:9000
```

Use same port locally and remotely:

```bash
ops k8s port-forward my-app 3000
```

Forward from a specific namespace:

```bash
ops k8s port-forward my-pod -n production 8080:8000
```

Listen on all network interfaces (allows remote connections):

```bash
ops k8s port-forward my-app 8080:8000 --address 0.0.0.0
```

Forward multiple services:

```bash
ops k8s port-forward svc/web 8080:80
# In another terminal:
ops k8s port-forward svc/api 8081:8000
```

**Example Output:**

```text
Resolved service 'my-service' to pod 'my-app-5d4d4d4d4-abc12'
Forwarding from 127.0.0.1:8080 -> 80
Forwarding from 127.0.0.1:9000 -> 9000
Press Ctrl+C to stop port forwarding.
[stays running, waiting for connections]
```

**Example Output (when stopped):**

```text
^C
Stopping port forwarding...
```

**Access Examples:**

Once port-forward is running, access your service locally:

```bash
# From the same machine
curl http://localhost:8080
wget http://127.0.0.1:8080/api/status

# In a web browser
# Navigate to http://localhost:8080
```

**Development Workflow:**

```bash
# Terminal 1: Start port-forward to your service
ops k8s port-forward my-app 3000:8000 --address 0.0.0.0

# Terminal 2: Run local tests that connect to the service
npm test --server http://localhost:3000

# Terminal 3: Or develop locally
curl http://localhost:3000/api/users
```

**Notes:**

- Default address `127.0.0.1` only accepts local connections; use `0.0.0.0` for network access
- Enabling network access (`0.0.0.0`) reduces security; consider firewall restrictions
- Each port mapping requires a separate `ops k8s port-forward` command or multiple mappings in one command
- Port numbers must be between 1 and 65535
- Ports below 1024 require elevated privileges (run with `sudo` if needed)
- Service resolution occurs once at connection time; if the service's pods change, the old tunnel remains active
- Port-forward maintains a persistent connection; network interruptions require reconnection
- Press Ctrl+C to cleanly stop forwarding without errors

---

## Example Workflows

### Debugging a Failing Application

```bash
# Terminal 1: Stream logs to see what's happening
ops k8s logs my-app -f --timestamps

# Terminal 2: Connect to the pod for interactive debugging
ops k8s exec my-app -it -- /bin/bash

# Inside the container:
root@my-app:/# cat /app/config.yaml
root@my-app:/# curl http://localhost:8000/health
root@my-app:/# exit
```

### Development Against a Remote Service

```bash
# Terminal 1: Port-forward the remote database
ops k8s port-forward svc/postgres 5432:5432 -n production

# Terminal 2: Port-forward the remote cache
ops k8s port-forward svc/redis 6379:6379 -n production

# Terminal 3: Run your local application
# Configure your app to connect to localhost:5432 and localhost:6379
npm start
```

### Monitoring a Deployment Rollout

```bash
# Watch logs from multiple pods during a deployment
ops k8s logs my-app-deployment-abc123 -f --timestamps &
ops k8s logs my-app-deployment-def456 -f --timestamps &

# Or check specific container logs
ops k8s logs my-app -f -c app --timestamps
ops k8s logs my-app -f -c sidecar --timestamps
```

### Troubleshooting Configuration Issues

```bash
# Check what the application sees
ops k8s exec my-app -- env | grep CONFIG

# Verify mounted volumes
ops k8s exec my-app -- ls -la /mnt/config/

# Check application startup
ops k8s logs my-app --previous  # Logs from previous instance if crashed
ops k8s logs my-app --since 5m  # Logs from the last 5 minutes
```

### Container Verification Before Applying to Production

```bash
# Get an interactive shell and verify configuration
ops k8s exec my-test-pod -n staging -it

# Inside the container:
root@my-test-pod:/# ./healthcheck.sh
root@my-test-pod:/# /app/migrate.sh --status
root@my-test-pod:/# exit

# If OK, proceed with production deployment
ops k8s manifests apply ./k8s/ -n production
```

---

## Troubleshooting

| Issue                                  | Cause                             | Solution             |
| -------------------------------------- | --------------------------------- | -------------------- |
| "Pod not found"                        | Pod doesn't exist in              | Check namespace:     |
| "Container not found"                  | Container name doesn't exist      | List containers:     |
| "Connection refused"                   | Port-forward target isn't         | Verify the service/p |
| Logs appear empty                      | Pod hasn't generated logs yet or  | Try `--tail 100` to  |
| "No such file or directory" in exec    | Command or shell doesn't exist    | Use `ops k8s exec    |
| Interactive exec hangs                 | TTY allocation issue              | Try without `-t`     |
| Port-forward fails with "Address       | Local port is already in use      | Use a different      |
| Can't connect to forwarded port from   | Address bound to 127.0.0.1 only   | Use `--address       |
| Previous logs unavailable              | Container hasn't crashed, or logs | Only available       |
| "Cannot connect to Kubernetes cluster" | kubeconfig invalid or cluster     | Verify cluster       |
| Exec returns wrong                     | Command failed in container       | The command's        |

---

## See Also

- [Kubernetes Plugin Index](../index.md)
- [Manifests Commands](manifests.md) - YAML manifest validation and deployment
- [Optimization Commands](optimization.md) - Resource analysis and recommendations
- [Workloads Commands](workloads.md) - Pod and workload management
- [Examples and Use Cases](../examples.md) - Complete workflow examples
- [TUI Overview](../tui.md) - Terminal user interface for Kubernetes management
