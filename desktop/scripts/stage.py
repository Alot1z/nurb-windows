from __future__ import annotations

import hashlib
import os
import platform
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TAURI = ROOT / 'desktop' / 'src-tauri'
RESOURCES = TAURI / 'resources'
BINARIES = TAURI / 'binaries'
UV_VERSION = '0.12.1'


def target_triple() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    if system == 'windows':
        return 'aarch64-pc-windows-msvc' if machine in {'arm64', 'aarch64'} else 'x86_64-pc-windows-msvc'
    if system == 'darwin':
        return 'aarch64-apple-darwin' if machine in {'arm64', 'aarch64'} else 'x86_64-apple-darwin'
    if system == 'linux':
        return 'aarch64-unknown-linux-gnu' if machine in {'arm64', 'aarch64'} else 'x86_64-unknown-linux-gnu'
    raise RuntimeError(f'Unsupported platform: {platform.system()} {platform.machine()}')


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={'User-Agent': 'nurb-windows-stager'})
    with urllib.request.urlopen(request) as response, destination.open('wb') as fh:
        shutil.copyfileobj(response, fh)


def fetch_uv(target: str) -> Path:
    suffixes = ['.zip', '.tar.gz'] if 'windows' in target else ['.tar.gz']
    destination = BINARIES / ('uv-' + target + ('.exe' if 'windows' in target else ''))
    if destination.exists():
        return destination
    BINARIES.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        archive = None
        archive_url = None
        for suffix in suffixes:
            candidate = tmp / ('uv' + suffix)
            url = f'https://github.com/astral-sh/uv/releases/download/{UV_VERSION}/uv-{target}{suffix}'
            try:
                download(url, candidate)
                archive_url = url
                archive = candidate
                break
            except Exception:
                if candidate.exists():
                    candidate.unlink()
        if archive is None:
            raise RuntimeError(f'Could not download uv {UV_VERSION} for {target}')
        checksum = tmp / (archive.name + '.sha256')
        assert archive_url is not None
        download(archive_url + '.sha256', checksum)
        expected = checksum.read_text(encoding='utf-8').split()[0].lower()
        actual = sha256(archive)
        if expected != actual:
            raise RuntimeError(f'SHA-256 mismatch for {archive.name}')
        extract = tmp / 'extract'
        extract.mkdir()
        if archive.suffix == '.zip':
            with zipfile.ZipFile(archive) as zf:
                zf.extractall(extract)
        else:
            subprocess.run(['tar', '-xzf', str(archive), '-C', str(extract)], check=True)
        found = next(extract.rglob('uv.exe' if 'windows' in target else 'uv'), None)
        if found is None:
            raise RuntimeError('uv executable was not found in the archive')
        shutil.copy2(found, destination)
    if os.name != 'nt':
        destination.chmod(0o755)
    return destination


def main() -> int:
    target = target_triple()
    RESOURCES.mkdir(parents=True, exist_ok=True)
    BINARIES.mkdir(parents=True, exist_ok=True)
    subprocess.run(['uv', 'build', '--wheel', '--project', str(ROOT), '-o', str(RESOURCES)], check=True)
    requirements = RESOURCES / 'requirements.lock'
    subprocess.run(['uv', 'pip', 'compile', str(ROOT / 'pyproject.toml'), '--universal', '--python-version', '3.13', '--generate-hashes', '--no-annotate', '-q', '-o', str(requirements)], check=True)
    adapter = ROOT / 'desktop' / 'adapter-runtime'
    shutil.copy2(adapter / 'package.json', RESOURCES / 'adapter-package.json')
    shutil.copy2(adapter / 'package-lock.json', RESOURCES / 'adapter-package-lock.json')
    uv = fetch_uv(target)
    print(f'stage: ready for {target}: {uv}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
