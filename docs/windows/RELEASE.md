# Windows release

Primary artifact:

-
nurb-windows-x64-setup.exe (NSIS)

Optional:

- MSI package for managed deployments.

Release requirements:

- Windows Tauri build succeeds.
- Python package tests pass.
- Desktop tests pass.
- Installer smoke test passes.
- Application executable is Authenticode-signed.
- Tauri updater artifacts are signed with the fork's updater key.
- Updater endpoint points only at Alot1z/nurb-windows.
