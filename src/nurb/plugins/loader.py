"""Plugin discovery and loading.

Scans plugin directories for subdirectories containing ``plugin.toml``.
Validates each manifest, imports ``plugin.py`` if present, and calls its
``register()`` function to let the plugin wire up commands and tools.

A broken plugin is logged and skipped; it never prevents other plugins from
loading or nurb from starting.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path

from .manifest import ManifestError, parse_manifest
from .registry import PluginState, registry

log = logging.getLogger(__name__)


def _builtin_dir() -> Path:
    """The shipped plugin directory: repo-root plugins/ in a source checkout.

    Resolved from this file's location rather than cwd, so it works regardless
    of where nurb is invoked from. When nurb is installed as a package the
    examples live next to the package data, so the parent of src/nurb is
    walked until a plugins/ directory with plugin.toml manifests is found.
    """
    here = Path(__file__).resolve()
    # src/nurb/plugins/loader.py -> repo root is three parents up
    root = here.parents[3] if here.parents else here.parent
    candidate = root / "plugins"
    if (candidate / "examples").is_dir():
        return candidate
    # Fall back to the package-adjacent location.
    for parent in here.parents:
        trial = parent / "plugins"
        if trial.is_dir() and not trial.name.startswith("."):
            return trial
    return candidate


_BUILTIN_DIR = _builtin_dir()
_USER_DIR = Path.home() / ".nurb" / "plugins"


def _plugin_dirs(project_root: Path | None = None) -> list[Path]:
    """Ordered list of plugin directories to scan. Later dirs win on ID collision."""
    dirs = []
    if _BUILTIN_DIR.is_dir():
        dirs.append(_BUILTIN_DIR)
    if project_root:
        proj_plugins = project_root / "plugins"
        if proj_plugins.is_dir():
            dirs.append(proj_plugins)
    if _USER_DIR.is_dir():
        dirs.append(_USER_DIR)
    # The repo-root plugins/ dir is both the builtin and the project dir in a
    # source checkout; scanning it twice re-imports every module for nothing.
    seen = []
    for d in dirs:
        resolved = d.resolve()
        if resolved not in seen:
            seen.append(resolved)
            yield d


def _candidate_dirs(plugin_dir: Path):
    """Directories inside a plugin dir that may hold a plugin.

    A plugin is a directory containing plugin.toml. The shipped dir also nests
    its examples one level down (plugins/examples/<name>/), so both direct
    children and plugins/examples/* are candidates.
    """
    for child in sorted(plugin_dir.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith("_") or child.name.startswith("."):
            continue  # template and hidden dirs are never loaded
        yield child
    examples = plugin_dir / "examples"
    if examples.is_dir():
        for child in sorted(examples.iterdir()):
            if not child.is_dir():
                continue
            if child.name.startswith("_") or child.name.startswith("."):
                continue
            yield child


def _import_plugin(plugin_dir: Path, plugin_id: str):
    """Import ``plugin.py`` from a plugin directory.

    Returns the imported module or None if no plugin.py exists.
    Raises on import errors (caller decides whether to skip).
    """
    plugin_py = plugin_dir / "plugin.py"
    if not plugin_py.is_file():
        return None
    module_name = f"nurb_plugin_{plugin_id}"
    spec = importlib.util.spec_from_file_location(module_name, plugin_py)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot create module spec for {plugin_py}")
    module = importlib.util.module_from_spec(spec)
    # Temporarily add the plugin directory to sys.path so relative imports work.
    plugin_dir_str = str(plugin_dir)
    old_path = sys.path.copy()
    if plugin_dir_str not in sys.path:
        sys.path.insert(0, plugin_dir_str)
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = old_path
    return module


def _nurb_version() -> str | None:
    """The running nurb version, or None if it cannot be determined."""
    import importlib.metadata

    try:
        return importlib.metadata.version("nurb")
    except importlib.metadata.PackageNotFoundError:
        return None


def load_plugin(plugin_dir: Path) -> bool:
    """Load a single plugin from a directory. Returns True on success."""
    manifest_path = plugin_dir / "plugin.toml"
    try:
        manifest = parse_manifest(manifest_path)
    except ManifestError as exc:
        log.warning("skipping broken plugin in %s: %s", plugin_dir, exc)
        registry.mark_error(f"{plugin_dir.name}:{manifest_path.name}", str(exc))
        return False
    except Exception as exc:
        log.warning("skipping plugin in %s: %s", plugin_dir, exc)
        registry.mark_error(f"{plugin_dir.name}:{manifest_path.name}", str(exc))
        return False

    # Check nurb version compatibility.
    nurb_version = _nurb_version()
    if nurb_version and not manifest.is_compatible(nurb_version):
        log.info(
            "skipping incompatible plugin %s (requires nurb %s%s, have %s)",
            manifest.id,
            ">=" if manifest.min_nurb else "",
            manifest.min_nurb or manifest.max_nurb,
            nurb_version,
        )
        registry.mark_error(
            manifest.id,
            f"incompatible with nurb {nurb_version} (requires {manifest.min_nurb or '?'}..{manifest.max_nurb or 'any'})",
        )
        return False

    # Register the plugin identity.
    record = registry.register(
        plugin_id=manifest.id,
        name=manifest.name,
        version=manifest.version,
    )

    # Import plugin.py if it exists.
    module = None
    if (plugin_dir / "plugin.py").is_file():
        try:
            module = _import_plugin(plugin_dir, manifest.id)
            record.module = module
        except Exception as exc:
            error_msg = f"import error: {exc}"
            log.warning("plugin %s failed to import: %s", manifest.id, exc)
            registry.mark_error(manifest.id, error_msg)
            return False

    # Call the plugin's register() function if present.
    if module and hasattr(module, "register"):
        try:
            module.register(registry, manifest)
        except Exception as exc:
            error_msg = f"register() failed: {exc}"
            log.warning("plugin %s register() failed: %s", manifest.id, exc)
            registry.mark_error(manifest.id, error_msg)
            return False

    return True


def load_all(project_root: Path | None = None) -> int:
    """Discover and load all plugins from all configured directories.

    Returns the number of plugins successfully loaded.
    """
    loaded = 0
    for plugin_dir in _plugin_dirs(project_root):
        for child in _candidate_dirs(plugin_dir):
            if not (child / "plugin.toml").is_file():
                continue  # not a plugin
            if load_plugin(child):
                loaded += 1
    return loaded
