# Hot Loading

Dynamic plugin loading and reloading capabilities for seamless development and runtime plugin
management without system restarts.

## Overview

Hot loading features:

- **Runtime Loading**: Load plugins without restarting the system
- **Automatic Reloading**: Watch for file changes and reload automatically
- **Dependency Management**: Handle plugin dependencies during reload
- **State Preservation**: Maintain system state during plugin updates
- **Safe Reloading**: Validate plugins before activation
- **Development Mode**: Enhanced features for plugin development

## Configuration

### Hot Loading Settings

```yaml
# config/hot-loading.yaml
hot_loading:
  enabled: true
  development_mode: true

  # File watching
  watch:
    enabled: true
    patterns:
      - "plugins/**/*.py"
      - "config/**/*.yaml"
      - "schemas/**/*.json"
    ignore:
      - "**/__pycache__/**"
      - "**/*.pyc"
      - "**/.*"

  # Reload behavior
  reload:
    automatic: true
    validation: true
    backup_state: true
    timeout: 30

  # Development features
  development:
    debug_logging: true
    preserve_breakpoints: true
    auto_install_deps: true
    reload_on_import_error: true

  # Safety features
  safety:
    validate_before_reload: true
    rollback_on_failure: true
    max_reload_attempts: 3
    cooldown_period: 5
```

## Basic Usage

### Loading Plugins

```bash
# Load a plugin at runtime
sysctl plugins load my-plugin --path /path/to/plugin

# Load from package
sysctl plugins load system-control-monitoring --from-package

# Load with specific version
sysctl plugins load my-plugin --version 2.1.0

# Load in development mode
sysctl plugins load my-plugin --dev-mode --watch
```

### Reloading Plugins

```bash
# Reload specific plugin
sysctl plugins reload my-plugin

# Reload all plugins
sysctl plugins reload --all

# Force reload (skip validation)
sysctl plugins reload my-plugin --force

# Reload with backup
sysctl plugins reload my-plugin --backup-state
```

### Plugin Status

```bash
# Check plugin status
sysctl plugins status

# Detailed plugin info
sysctl plugins info my-plugin

# Show loaded plugins
sysctl plugins list --loaded

# Show plugin dependencies
sysctl plugins deps my-plugin
```

## Automatic File Watching

### File System Monitoring

```python
# Internal file watcher implementation
import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class PluginWatcher(FileSystemEventHandler):
    """Watch plugin files for changes."""

    def __init__(self, hot_loader):
        self.hot_loader = hot_loader
        self.reload_queue = asyncio.Queue()
        self.cooldown = {}

    def on_modified(self, event):
        """Handle file modification."""
        if event.is_directory:
            return

        file_path = event.src_path

        # Check if file is a plugin
        plugin_name = self.identify_plugin(file_path)
        if not plugin_name:
            return

        # Apply cooldown to prevent rapid reloads
        current_time = time.time()
        last_reload = self.cooldown.get(plugin_name, 0)

        if current_time - last_reload < 2:  # 2 second cooldown
            return

        # Queue plugin for reload
        asyncio.create_task(self.reload_queue.put({
            'plugin': plugin_name,
            'file_path': file_path,
            'timestamp': current_time
        }))

    def identify_plugin(self, file_path: str) -> str:
        """Identify plugin from file path."""
        # Logic to map file paths to plugin names
        for plugin_name, plugin in self.hot_loader.loaded_plugins.items():
            if file_path in plugin.source_files:
                return plugin_name
        return None

class HotLoader:
    """Hot loading manager."""

    def __init__(self, config):
        self.config = config
        self.loaded_plugins = {}
        self.observer = None
        self.watcher = PluginWatcher(self)

    async def start_watching(self):
        """Start file system monitoring."""
        if not self.config.get("watch", {}).get("enabled"):
            return

        self.observer = Observer()

        # Watch plugin directories
        watch_paths = [
            "plugins/",
            "config/",
            "schemas/"
        ]

        for path in watch_paths:
            if os.path.exists(path):
                self.observer.schedule(
                    self.watcher,
                    path,
                    recursive=True
                )

        self.observer.start()

        # Start reload processor
        asyncio.create_task(self.process_reload_queue())

    async def process_reload_queue(self):
        """Process plugin reload requests."""
        while True:
            try:
                reload_request = await self.watcher.reload_queue.get()
                await self.reload_plugin(reload_request['plugin'])

            except Exception as e:
                logger.error(f"Error processing reload: {e}")
```

### Development Mode

```bash
# Start system in development mode
sysctl --dev-mode start

# Enable hot loading for specific plugin
sysctl plugins dev my-plugin --watch --auto-reload

# Development server with hot loading
sysctl dev server --port 8080 --hot-reload
```

## Safe Plugin Reloading

### Validation Pipeline

```python
class PluginValidator:
    """Validate plugins before hot loading."""

    def __init__(self):
        self.validators = [
            self.validate_syntax,
            self.validate_imports,
            self.validate_plugin_class,
            self.validate_dependencies,
            self.validate_compatibility
        ]

    async def validate_plugin(self, plugin_path: str) -> ValidationResult:
        """Run full validation pipeline."""
        result = ValidationResult()

        for validator in self.validators:
            try:
                await validator(plugin_path, result)

            except ValidationError as e:
                result.add_error(f"Validation failed: {e}")
                break

        return result

    async def validate_syntax(self, plugin_path: str, result: ValidationResult):
        """Validate Python syntax."""
        try:
            with open(plugin_path, 'r') as f:
                source = f.read()

            compile(source, plugin_path, 'exec')
            result.add_success("Syntax validation passed")

        except SyntaxError as e:
            raise ValidationError(f"Syntax error: {e}")

    async def validate_imports(self, plugin_path: str, result: ValidationResult):
        """Validate all imports are available."""
        import ast

        with open(plugin_path, 'r') as f:
            source = f.read()

        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.check_import_available(alias.name)

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self.check_import_available(node.module)

        result.add_success("Import validation passed")

    def check_import_available(self, module_name: str):
        """Check if module can be imported."""
        try:
            __import__(module_name)
        except ImportError:
            raise ValidationError(f"Module not available: {module_name}")

    async def validate_plugin_class(self, plugin_path: str, result: ValidationResult):
        """Validate plugin class structure."""
        # Load plugin temporarily to check structure
        spec = importlib.util.spec_from_file_location("temp_plugin", plugin_path)
        module = importlib.util.module_from_spec(spec)

        try:
            spec.loader.exec_module(module)
        except Exception as e:
            raise ValidationError(f"Failed to load plugin: {e}")

        # Find plugin class
        plugin_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and
                issubclass(attr, Plugin) and
                attr is not Plugin):
                plugin_class = attr
                break

        if not plugin_class:
            raise ValidationError("No plugin class found")

        # Validate required attributes
        required_attrs = ['name', 'version']
        for attr in required_attrs:
            if not hasattr(plugin_class, attr) or getattr(plugin_class, attr) is None:
                raise ValidationError(f"Missing required attribute: {attr}")

        result.add_success("Plugin class validation passed")
```

### Rollback on Failure

```python
class SafeReloader:
    """Safe plugin reloading with rollback."""

    def __init__(self, hot_loader):
        self.hot_loader = hot_loader
        self.backups = {}

    async def safe_reload(self, plugin_name: str) -> ReloadResult:
        """Safely reload plugin with rollback capability."""
        result = ReloadResult()

        try:
            # Create backup of current state
            backup = await self.create_backup(plugin_name)
            self.backups[plugin_name] = backup

            # Validate new plugin version
            validation = await self.validate_plugin(plugin_name)
            if not validation.is_valid:
                result.add_errors(validation.errors)
                return result

            # Perform reload
            await self.perform_reload(plugin_name)

            # Verify reload was successful
            if not await self.verify_plugin_health(plugin_name):
                raise ReloadError("Plugin health check failed")

            result.success = True
            result.message = f"Plugin {plugin_name} reloaded successfully"

        except Exception as e:
            # Rollback on failure
            await self.rollback_plugin(plugin_name)
            result.success = False
            result.error = str(e)

        return result

    async def create_backup(self, plugin_name: str) -> PluginBackup:
        """Create backup of plugin state."""
        plugin = self.hot_loader.get_plugin(plugin_name)

        backup = PluginBackup(
            plugin_name=plugin_name,
            timestamp=datetime.utcnow(),
            plugin_state=copy.deepcopy(plugin.__dict__),
            configuration=plugin.get_config(),
            active_commands=list(plugin.registered_commands.keys())
        )

        return backup

    async def rollback_plugin(self, plugin_name: str):
        """Rollback plugin to previous state."""
        if plugin_name not in self.backups:
            raise RollbackError(f"No backup available for {plugin_name}")

        backup = self.backups[plugin_name]

        # Restore plugin state
        await self.hot_loader.unload_plugin(plugin_name)
        await self.hot_loader.load_plugin_from_backup(backup)

        logger.info(f"Rolled back plugin {plugin_name} to {backup.timestamp}")
```

## State Preservation

### Plugin State Management

```python
class StateManager:
    """Manage plugin state during reloads."""

    def __init__(self):
        self.state_store = {}
        self.persistent_objects = {}

    async def preserve_state(self, plugin: Plugin) -> StateSnapshot:
        """Preserve plugin state before reload."""
        snapshot = StateSnapshot(plugin.name)

        # Preserve instance variables
        for attr_name, attr_value in plugin.__dict__.items():
            if not attr_name.startswith('_'):
                snapshot.add_attribute(attr_name, copy.deepcopy(attr_value))

        # Preserve persistent objects
        if hasattr(plugin, 'get_persistent_state'):
            persistent_state = plugin.get_persistent_state()
            snapshot.persistent_state = persistent_state

        # Preserve active connections
        if hasattr(plugin, 'active_connections'):
            snapshot.connections = plugin.active_connections

        return snapshot

    async def restore_state(self, plugin: Plugin, snapshot: StateSnapshot):
        """Restore plugin state after reload."""

        # Restore instance variables
        for attr_name, attr_value in snapshot.attributes.items():
            setattr(plugin, attr_name, attr_value)

        # Restore persistent state
        if snapshot.persistent_state and hasattr(plugin, 'restore_persistent_state'):
            plugin.restore_persistent_state(snapshot.persistent_state)

        # Restore connections
        if snapshot.connections and hasattr(plugin, 'restore_connections'):
            plugin.restore_connections(snapshot.connections)

        logger.info(f"Restored state for plugin {plugin.name}")
```

### Connection Management

```python
class ConnectionManager:
    """Manage persistent connections during plugin reloads."""

    def __init__(self):
        self.connection_pool = {}

    def register_connection(self, plugin_name: str, connection_id: str, connection):
        """Register a persistent connection."""
        if plugin_name not in self.connection_pool:
            self.connection_pool[plugin_name] = {}

        self.connection_pool[plugin_name][connection_id] = connection

    def get_connection(self, plugin_name: str, connection_id: str):
        """Get a persistent connection."""
        return self.connection_pool.get(plugin_name, {}).get(connection_id)

    async def transfer_connections(self, plugin_name: str, old_plugin: Plugin, new_plugin: Plugin):
        """Transfer connections from old plugin to new plugin."""
        if plugin_name not in self.connection_pool:
            return

        connections = self.connection_pool[plugin_name]

        for connection_id, connection in connections.items():
            if hasattr(new_plugin, 'adopt_connection'):
                await new_plugin.adopt_connection(connection_id, connection)
            else:
                # Default connection transfer
                setattr(new_plugin, connection_id, connection)

        logger.info(f"Transferred {len(connections)} connections for {plugin_name}")
```

## Development Tools

### Plugin Development Server

```python
class PluginDevServer:
    """Development server with hot loading."""

    def __init__(self, config):
        self.config = config
        self.app = self.create_app()
        self.hot_loader = HotLoader(config)

    def create_app(self):
        """Create development web interface."""
        from flask import Flask, jsonify, request

        app = Flask(__name__)

        @app.route('/api/plugins')
        def list_plugins():
            """List all loaded plugins."""
            return jsonify([
                {
                    'name': name,
                    'version': plugin.version,
                    'status': plugin.status,
                    'last_loaded': plugin.last_loaded.isoformat()
                }
                for name, plugin in self.hot_loader.loaded_plugins.items()
            ])

        @app.route('/api/plugins/<name>/reload', methods=['POST'])
        def reload_plugin(name):
            """Reload specific plugin."""
            result = asyncio.run(self.hot_loader.reload_plugin(name))
            return jsonify(result.to_dict())

        @app.route('/api/plugins/<name>/status')
        def plugin_status(name):
            """Get plugin status."""
            plugin = self.hot_loader.get_plugin(name)
            if not plugin:
                return jsonify({'error': 'Plugin not found'}), 404

            return jsonify({
                'name': plugin.name,
                'version': plugin.version,
                'status': plugin.status,
                'health': plugin.health_check(),
                'commands': list(plugin.registered_commands.keys()),
                'last_loaded': plugin.last_loaded.isoformat(),
                'reload_count': plugin.reload_count
            })

        return app

    async def start(self):
        """Start development server."""
        # Start hot loader
        await self.hot_loader.start_watching()

        # Start web interface
        port = self.config.get('port', 8080)
        self.app.run(debug=True, port=port, use_reloader=False)
```

### CLI Development Commands

```bash
# Start development mode
sysctl dev mode --enable

# Create new plugin template
sysctl dev plugin create my-plugin --template command

# Validate plugin during development
sysctl dev plugin validate my-plugin --watch

# Test plugin with hot reloading
sysctl dev plugin test my-plugin --hot-reload

# Debug plugin loading
sysctl dev plugin debug my-plugin --verbose

# Monitor plugin performance
sysctl dev plugin monitor my-plugin --metrics

# Plugin dependency analysis
sysctl dev plugin analyze-deps my-plugin
```

## Advanced Features

### Dependency Hot Loading

```python
class DependencyManager:
    """Manage plugin dependencies during hot loading."""

    def __init__(self):
        self.dependency_graph = nx.DiGraph()
        self.reload_order = []

    def add_dependency(self, plugin: str, depends_on: str):
        """Add plugin dependency."""
        self.dependency_graph.add_edge(plugin, depends_on)

    def calculate_reload_order(self, target_plugin: str) -> List[str]:
        """Calculate optimal reload order."""
        # Find all plugins that depend on target
        dependents = list(nx.descendants(self.dependency_graph, target_plugin))

        # Add target plugin
        plugins_to_reload = [target_plugin] + dependents

        # Sort topologically
        subgraph = self.dependency_graph.subgraph(plugins_to_reload)
        reload_order = list(nx.topological_sort(subgraph))

        return reload_order

    async def reload_with_dependencies(self, plugin_name: str):
        """Reload plugin and all dependents."""
        reload_order = self.calculate_reload_order(plugin_name)

        for plugin in reload_order:
            await self.hot_loader.reload_plugin(plugin)
```

### Configuration Hot Reloading

```python
class ConfigHotLoader:
    """Hot reload configuration changes."""

    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.watchers = {}

    async def watch_config_files(self):
        """Watch configuration files for changes."""
        config_files = [
            "config/main.yaml",
            "config/plugins.yaml",
            "config/environments.yaml"
        ]

        for config_file in config_files:
            watcher = ConfigFileWatcher(config_file, self.on_config_change)
            self.watchers[config_file] = watcher
            await watcher.start()

    async def on_config_change(self, file_path: str):
        """Handle configuration file changes."""
        logger.info(f"Configuration file changed: {file_path}")

        try:
            # Reload configuration
            await self.config_manager.reload_config(file_path)

            # Find affected plugins
            affected_plugins = self.find_affected_plugins(file_path)

            # Reload affected plugins
            for plugin_name in affected_plugins:
                await self.hot_loader.reload_plugin(plugin_name)

        except Exception as e:
            logger.error(f"Failed to reload config {file_path}: {e}")

    def find_affected_plugins(self, config_file: str) -> List[str]:
        """Find plugins affected by configuration change."""
        affected = []

        for plugin_name, plugin in self.hot_loader.loaded_plugins.items():
            if hasattr(plugin, 'config_dependencies'):
                if config_file in plugin.config_dependencies:
                    affected.append(plugin_name)

        return affected
```

## Performance Optimization

### Lazy Loading

```python
class LazyPluginLoader:
    """Lazy load plugins to improve startup time."""

    def __init__(self):
        self.plugin_registry = {}
        self.loaded_plugins = {}
        self.loading_promises = {}

    def register_plugin(self, name: str, path: str, metadata: dict):
        """Register plugin for lazy loading."""
        self.plugin_registry[name] = {
            'path': path,
            'metadata': metadata,
            'loaded': False
        }

    async def get_plugin(self, name: str) -> Plugin:
        """Get plugin, loading if necessary."""
        if name in self.loaded_plugins:
            return self.loaded_plugins[name]

        if name in self.loading_promises:
            return await self.loading_promises[name]

        # Start loading
        self.loading_promises[name] = self._load_plugin(name)

        try:
            plugin = await self.loading_promises[name]
            self.loaded_plugins[name] = plugin
            return plugin

        finally:
            del self.loading_promises[name]

    async def _load_plugin(self, name: str) -> Plugin:
        """Actually load the plugin."""
        if name not in self.plugin_registry:
            raise PluginNotFoundError(f"Plugin {name} not registered")

        plugin_info = self.plugin_registry[name]

        # Load plugin module
        spec = importlib.util.spec_from_file_location(name, plugin_info['path'])
        module = importlib.util.module_from_spec(spec)

        spec.loader.exec_module(module)

        # Find plugin class
        plugin_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and
                issubclass(attr, Plugin) and
                attr is not Plugin):
                plugin_class = attr
                break

        if not plugin_class:
            raise PluginError(f"No plugin class found in {name}")

        # Initialize plugin
        plugin = plugin_class()
        await plugin.initialize()

        return plugin
```

### Caching and Optimization

```python
class PluginCache:
    """Cache compiled plugins for faster loading."""

    def __init__(self, cache_dir: str = ".plugin_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def get_cache_key(self, plugin_path: str) -> str:
        """Generate cache key for plugin."""
        stat = os.stat(plugin_path)
        return f"{plugin_path}_{stat.st_mtime}_{stat.st_size}"

    def is_cached(self, plugin_path: str) -> bool:
        """Check if plugin is cached."""
        cache_key = self.get_cache_key(plugin_path)
        cache_file = self.cache_dir / f"{cache_key}.pyc"
        return cache_file.exists()

    def cache_plugin(self, plugin_path: str, compiled_code):
        """Cache compiled plugin."""
        cache_key = self.get_cache_key(plugin_path)
        cache_file = self.cache_dir / f"{cache_key}.pyc"

        with open(cache_file, 'wb') as f:
            marshal.dump(compiled_code, f)

    def load_cached(self, plugin_path: str):
        """Load plugin from cache."""
        cache_key = self.get_cache_key(plugin_path)
        cache_file = self.cache_dir / f"{cache_key}.pyc"

        with open(cache_file, 'rb') as f:
            return marshal.load(f)
```

## Troubleshooting

### Common Issues

```bash
# Plugin won't reload
sysctl plugins debug my-plugin --check-locks --check-dependencies

# File watching not working
sysctl plugins debug-watcher --test-events

# State not preserved during reload
sysctl plugins debug my-plugin --check-state-methods

# Performance issues during reload
sysctl plugins profile my-plugin --reload-time
```

### Debugging Tools

```python
class HotLoadingDebugger:
    """Debug hot loading issues."""

    def __init__(self, hot_loader):
        self.hot_loader = hot_loader

    def diagnose_reload_failure(self, plugin_name: str) -> DiagnosticReport:
        """Diagnose why plugin reload failed."""
        report = DiagnosticReport(plugin_name)

        # Check file permissions
        plugin_path = self.hot_loader.get_plugin_path(plugin_name)
        if not os.access(plugin_path, os.R_OK):
            report.add_issue("File permission denied")

        # Check file locks
        if self.is_file_locked(plugin_path):
            report.add_issue("Plugin file is locked by another process")

        # Check dependencies
        deps = self.check_dependencies(plugin_name)
        if deps.missing:
            report.add_issue(f"Missing dependencies: {deps.missing}")

        # Check syntax
        syntax_check = self.check_syntax(plugin_path)
        if not syntax_check.valid:
            report.add_issue(f"Syntax error: {syntax_check.error}")

        return report
```

## Best Practices

### Development Workflow

1. **Use Development Mode**: Enable development mode during plugin development
2. **Write Tests**: Include comprehensive tests for hot loading scenarios
3. **State Management**: Design plugins to handle state preservation
4. **Error Handling**: Implement proper error handling for reload failures
5. **Documentation**: Document plugin dependencies and reload behavior

### Performance Tips

1. **Lazy Loading**: Use lazy loading for non-critical plugins
2. **Caching**: Enable plugin compilation caching
3. **Selective Watching**: Watch only necessary files
4. **Batch Reloads**: Group related plugin reloads together
5. **Monitor Performance**: Track reload times and optimize bottlenecks
