# My Plugin

Copy this directory to `plugins/` in a nurb project (or `~/.nurb/plugins/`)
to make it load. Rename the directory, edit `plugin.toml` (id, name, version,
capabilities), then implement `plugin.py`.

## Files

- `plugin.toml` - the manifest: identity, version constraints, capabilities
- `plugin.py` - the implementation: imports, runs, and calls `register()`

## Lifecycle

1. The loader finds `plugin.toml` and validates it (id format, version format,
   required fields). A malformed manifest is rejected with a specific error.
2. `plugin.py` is imported and `register(registry, manifest)` is called.
3. Commands appear as `nurb <command-name>`; MCP tools appear in the nurb MCP
   server's tools/list; build checks run inside `nurb check`.
4. Any failure at any step marks the plugin as errored; other plugins and
   nurb itself keep working.

See `docs/windows/PLUGINS.md` for the full contract.
