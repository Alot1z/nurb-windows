# Windows porting guide

## Development prerequisites

Use Windows 10/11 x64 first. The supported engineering toolchain is Python 3.13, uv, Node.js, Rust/MSVC, and the Tauri CLI.

## Architecture rule

Keep upstream nurb behavior in `src/nurb/**` whenever possible. Put OS-specific behavior in `src/nurb/platform/**` or in the desktop Rust layer.

## Runtime

The desktop release provisions Python through the existing uv-based runtime and provisions its Node adapter runtime under app data. Windows uses `Scripts/` for Python executables and `node.exe` at the root of the Node archive.

## Process handling

Do not add ad-hoc `taskkill`, `process_group`, shell commands, or Windows-only subprocess flags inside feature modules. Route child ownership through `desktop/src-tauri/src/process.rs`.

## Paths

Use `pathlib.Path` in Python and `PathBuf` in Rust. Never construct a Windows path by concatenating slash-delimited strings.

## Shell/tool invocation

Prefer executable paths plus argument arrays. Avoid `shell=True`. When a platform command is unavoidable, isolate it in a platform layer and add a Windows test.

## Testing

At minimum run the Windows Python suite, desktop frontend tests, Tauri target compilation, and staging before considering a Windows change complete.

## Upstream changes

Run `python tools/upstream_sync.py status` before porting an upstream update. Review all `WINDOWS-SPECIFIC` and `REVIEW` files before merging.
