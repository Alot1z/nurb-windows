# Windows release

## Artifacts

The Windows release is built by `.github/workflows/windows-release.yml` when the
publish workflow tags a version (`vX.Y.Z`). It produces:

- `nurb_<version>_x64-setup.exe` (NSIS installer, also the updater bundle)
- `nurb_<version>_x64-setup.exe.sig` (minisign/Ed25519 updater signature)
- `latest.json` (static updater manifest, published as a release asset)

The installed app's updater endpoint is pinned to
`https://github.com/Alot1z/nurb-windows/releases/latest/download/latest.json`
(tauri.conf.json `plugins.updater.endpoints`). It only ever points at this
fork; never at upstream nurb's release channel.

## Signing keys

The updater uses one Ed25519 keypair:

- Public key: committed at `desktop/signing/tauri-updater.key.pub` and embedded
  in the app via `tauri.conf.json` `plugins.updater.pubkey` (base64 of the
  minisign text). Safe to share.
- Private key: NEVER committed. The file `desktop/signing/tauri-updater.key`
  is gitignored; in CI the key lives in the repository secrets
  `TAURI_SIGNING_PRIVATE_KEY` (key contents) and
  `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` (password). Losing it means existing
  installs can never receive an update, so keep a backup outside the repo.

Local signed builds load the gitignored key via:

```powershell
cd desktop
.\scripts\signing.ps1
npm run tauri -- build
```

Building with `createUpdaterArtifacts: true` and no private key fails loudly
rather than shipping an unsigned update channel.

## One-time secret setup

In the Alot1z/nurb-windows repository settings (Settings -> Secrets and
variables -> Actions) create:

| Secret | Value |
| --- | --- |
| `TAURI_SIGNING_PRIVATE_KEY` | contents of `desktop/signing/tauri-updater.key` |
| `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` | the key password |

Until these secrets exist, the windows-build workflow's build step (which signs
by default) fails by design.

## Releasing

1. Bump the version across `pyproject.toml`, `src/nurb/skill.md`,
   `skills/nurb/SKILL.md`, `desktop/src-tauri/tauri.conf.json`, and
   `desktop/src-tauri/Cargo.toml` (tests enforce agreement).
2. Merge to main. `publish.yml` creates the `vX.Y.Z` tag and GitHub release.
3. `windows-release.yml` runs on the tag, builds the signed installer, and
   attaches the installer, `.sig`, and `latest.json` to the release.
4. Smoke-test the release: install, launch, check for updates in the rail.

Authenticode signing of the .exe itself (SmartScreen) is separate from updater
signing and still TODO; the updater signatures above are what make in-app
updates secure.
