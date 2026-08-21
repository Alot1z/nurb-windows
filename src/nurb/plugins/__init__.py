"""nurb plugin system: discover, load, and manage third-party extensions.

A plugin is a directory containing a ``plugin.toml`` manifest and optionally a
``plugin.py`` module.  The manifest declares identity, capabilities, and
version constraints; the module provides the runtime implementations (commands,
MCP tools, build checks).

Three plugin directories are scanned at startup:

- ``plugins/`` in the nurb package directory (shipped examples/templates)
- ``<project>/plugins/`` if it exists (project-local plugins)
- ``~/.nurb/plugins/`` (user-installed plugins)

A broken plugin never prevents other plugins from loading or nurb from starting.
"""

from .manifest import ManifestError, PluginManifest, parse_manifest
from .registry import PluginState, registry
from .loader import load_all, load_plugin

__all__ = [
    "ManifestError",
    "PluginManifest",
    "PluginState",
    "load_all",
    "load_plugin",
    "parse_manifest",
    "registry",
]
