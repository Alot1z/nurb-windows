# nurb for Windows architecture

The Windows fork deliberately keeps the upstream nurb engine mergeable.

## Boundaries

- **Upstream-compatible:** src/nurb/** core behavior, 	ests/**, examples/**, skills/**, and evals/**.
- **Platform abstraction:** src/nurb/platform/**.
- **Windows desktop/distribution:** desktop/src-tauri/**, desktop/scripts/**, and Windows-focused GitHub Actions.
- **Sync tooling:** 	ools/** and docs/windows/**.

Windows-specific behavior should be isolated behind the platform layer whenever practical instead of adding sys.platform ==  win32 branches throughout the upstream code.

## Runtime

The desktop application bundles a pinned uv sidecar and the nurb wheel/lock files. The Windows build uses the x86_64-pc-windows-msvc target.

## SDK policy

The Windows SDK and MSVC toolchain are development/build prerequisites. WebView2 is the desktop web runtime used by Tauri on Windows. Windows App SDK/WinUI 3 is not a replacement for Tauri; use it only through a small native bridge when a Windows-only capability is genuinely useful.
