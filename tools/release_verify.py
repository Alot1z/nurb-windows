#!/usr/bin/env python3
"""Verify a Nurb-Windows release end to end, with the app's own semantics.

Downloads the actually published artifacts for a release tag and checks:

  - the Windows installer's minisign signature against the committed updater
    public key, using the same decoding and verification steps the desktop
    app performs at update time (base64 envelope -> minisign text -> key id
    match -> blake2b when prehashed -> Ed25519 -> global signature);
  - that latest.json advertises the same version as the tag, points its
    download URL at the release's own installer asset, and carries the same
    signature as the attached .sig file;
  - the installer's SHA-256 so provenance can be recorded.

This is the same check CI runs after windows-release attaches its artifacts
(python tools/release_verify.py --tag vX.Y.Z), so a broken release fails the
build instead of shipping. Local use: point --repo at the fork and run it for
any tag; it never touches the working tree beyond reading the committed key.

Exit code 0 means verified; anything else prints a one-line reason first.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

# --- pure-Python Ed25519 (RFC 8032), sign + verify -------------------------
# The desktop app verifies updater signatures with the minisign-verify crate;
# this is the same curve math in stdlib-only Python so the check can run
# anywhere `uv run python tools/release_verify.py` can. Cross-checked against
# the crate and against `cryptography` on real release artifacts.

_P = 2**255 - 19
_L = 2**252 + 27742317777372353535851937790883648493
_D = (-121665 * pow(121666, _P - 2, _P)) % _P
_I = pow(2, (_P - 1) // 4, _P)


def _xrecover(y):
    xx = (y * y - 1) * pow(_D * y * y + 1, _P - 2, _P)
    x = pow(xx, (_P + 3) // 8, _P)
    if (x * x - xx) % _P != 0:
        x = (x * _I) % _P
    if x % 2 != 0:
        x = _P - x
    return x


_BY = 4 * pow(5, _P - 2, _P) % _P
_BX = _xrecover(_BY)
_B = (_BX % _P, _BY % _P)


def _edwards(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    x3 = (x1 * y2 + x2 * y1) * pow(1 + _D * x1 * x2 * y1 * y2, _P - 2, _P) % _P
    y3 = (y1 * y2 + x1 * x2) * pow(1 - _D * x1 * x2 * y1 * y2, _P - 2, _P) % _P
    return x3, y3


def _scalarmult(p1, e):
    if e == 0:
        return (0, 1)
    q = _scalarmult(p1, e // 2)
    q = _edwards(q, q)
    if e & 1:
        q = _edwards(q, p1)
    return q


def _encodepoint(p1):
    x, y = p1
    bits = [(y >> i) & 1 for i in range(255)] + [x & 1]
    return bytes(
        sum(bits[i * 8 + j] << j for j in range(8)) for i in range(32)
    )


def _point_from_bytes(public_key):
    y = int.from_bytes(public_key, "little") & ((1 << 255) - 1)
    x = _xrecover(y)
    if (x & 1) != ((public_key[31] >> 7) & 1):
        x = _P - x
    return x, y


def ed25519_verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
    """RFC 8032 verification. Returns True only for a valid signature."""
    if len(public_key) != 32 or len(signature) != 64:
        return False
    a_point = _point_from_bytes(public_key)
    r_point = _point_from_bytes(signature[:32])
    s = int.from_bytes(signature[32:], "little")
    if s >= _L:
        return False
    h = (
        int.from_bytes(
            hashlib.sha512(_encodepoint(r_point) + public_key + message).digest(),
            "little",
        )
        % _L
    )
    return _scalarmult(_B, s) == _edwards(r_point, _scalarmult(a_point, h))


def ed25519_keypair(seed: bytes):
    """RFC 8032 keypair from a 32-byte seed. Returns (seed, public)."""
    h = hashlib.sha512(seed).digest()
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    return seed, _encodepoint(_scalarmult(_B, a))


def ed25519_sign(seed: bytes, message: bytes) -> bytes:
    """RFC 8032 signature from a 32-byte seed."""
    h = hashlib.sha512(seed).digest()
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    a_point = _encodepoint(_scalarmult(_B, a))
    r = int.from_bytes(hashlib.sha512(h[32:] + message).digest(), "little") % _L
    r_point = _encodepoint(_scalarmult(_B, r))
    hram = (
        int.from_bytes(hashlib.sha512(r_point + a_point + message).digest(), "little")
        % _L
    )
    s = (r + hram * a) % _L
    return r_point + s.to_bytes(32, "little")


# --- minisign format, matching minisign-verify's exact semantics -----------


class MinisignError(Exception):
    pass


def _decode_b64(text: str) -> bytes:
    try:
        return base64.b64decode(text.encode("ascii"), validate=True)
    except Exception as exc:  # binascii.Error / ValueError
        raise MinisignError(f"invalid base64: {exc}") from exc


def parse_public_key(text: str):
    """Two-line minisign pubkey text -> (key_id, key_bytes, algorithm)."""
    lines = text.splitlines()
    if len(lines) < 2:
        raise MinisignError("public key must have an untrusted comment and a key line")
    blob = _decode_b64(lines[1])
    if len(blob) != 42:
        raise MinisignError(f"public key blob is {len(blob)} bytes, expected 42")
    alg = blob[:2]
    if alg not in (b"Ed", b"ED"):
        raise MinisignError(f"unsupported signature algorithm {alg!r}")
    return blob[2:10], blob[10:42], alg


def parse_signature(text: str):
    """Four-line minisign signature text -> (key_id, sig64, global64, prehashed)."""
    lines = text.splitlines()
    if len(lines) < 4:
        raise MinisignError("signature must have 4 lines (comment, blob, comment, blob)")
    if not lines[2].startswith("trusted comment: "):
        raise MinisignError("signature lacks a trusted comment")
    blob = _decode_b64(lines[1])
    if len(blob) != 74:
        raise MinisignError(f"signature blob is {len(blob)} bytes, expected 74")
    global_blob = _decode_b64(lines[3])
    if len(global_blob) != 64:
        raise MinisignError(f"global signature is {len(global_blob)} bytes, expected 64")
    alg = blob[:2]
    if alg not in (b"Ed", b"ED"):
        raise MinisignError(f"unsupported signature algorithm {alg!r}")
    return (
        blob[2:10],
        blob[10:74],
        global_blob,
        alg == b"ED",  # prehashed mode hashes the file with blake2b first
    )


def verify_minisign(pubkey_text: str, sig_text: str, data: bytes) -> None:
    """Verify `data` against a minisign signature. Raises MinisignError."""
    key_id, key, _ = parse_public_key(pubkey_text)
    sig_key_id, sig, global_sig, prehashed = parse_signature(sig_text)
    if key_id != sig_key_id:
        raise MinisignError(
            f"key id mismatch: pubkey {key_id.hex()} vs signature {sig_key_id.hex()}"
        )
    signed = data
    if prehashed:
        signed = hashlib.blake2b(data, digest_size=64).digest()
    if not ed25519_verify(key, signed, sig):
        raise MinisignError("Ed25519 signature over the artifact does not verify")
    trusted = sig_text.splitlines()[2][len("trusted comment: "):].encode("utf-8")
    if not ed25519_verify(key, sig + trusted, global_sig):
        raise MinisignError("global signature over the trusted comment does not verify")


def load_pubkey_envelope(path: Path) -> str:
    """The committed key file is the base64 of the two-line minisign text."""
    raw = path.read_text(encoding="utf-8").strip()
    try:
        text = base64.b64decode(raw).decode("utf-8")
    except Exception as exc:
        raise MinisignError(f"committed pubkey is not base64 of minisign text: {exc}")
    if "minisign public key" not in text.splitlines()[0]:
        raise MinisignError("committed pubkey envelope does not decode to a minisign key")
    return text


def fetch(url: str, dest: Path) -> None:
    """Download with retries: a freshly attached asset can lag a moment."""
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "nurb-release-verify"})
            with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "wb") as out:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    out.write(chunk)
            return
        except (OSError, urllib.error.URLError) as exc:
            last = exc
            if attempt < 2:
                time.sleep(5 * (attempt + 1))
    raise last  # type: ignore[misc]


def latest_json_platform(meta: dict) -> str:
    """Pick the NSIS entry when present (that is the file the updater installs)."""
    if "windows-x86_64-nsis" in meta.get("platforms", {}):
        return "windows-x86_64-nsis"
    return "windows-x86_64"


def verify_release(
    tag: str,
    repo: str,
    pubkey_path: Path,
    scratch: Path,
    offline: bool = False,
    expected_sha256: str | None = None,
) -> dict:
    """Verify the published artifacts for `tag`. Returns a provenance dict."""
    version = tag[1:] if tag.startswith("v") else tag
    pubkey_text = load_pubkey_envelope(pubkey_path)
    key_id, _, alg = parse_public_key(pubkey_text)
    findings = []

    latest_path = scratch / "latest.json"
    sig_path = scratch / "release.sig"
    installer_path = scratch / "installer.exe"
    if not offline:
        base = f"https://github.com/{repo}/releases/download/{tag}"
        fetch(f"{base}/latest.json", latest_path)
        fetch(f"{base}/nurb_{version}_x64-setup.exe.sig", sig_path)
        fetch(f"{base}/nurb_{version}_x64-setup.exe", installer_path)
    elif not (latest_path.is_file() and sig_path.is_file() and installer_path.is_file()):
        raise MinisignError("offline mode needs latest.json, release.sig, installer.exe in scratch")

    try:
        meta = json.loads(latest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MinisignError(f"latest.json is malformed: {exc}") from exc

    if meta.get("version") != version:
        raise MinisignError(
            f"latest.json version {meta.get('version')!r} != tag version {version!r}"
        )

    platform = latest_json_platform(meta)
    entry = meta["platforms"][platform]
    sig_field = entry["signature"]
    url = entry["url"]

    expected_url = f"https://github.com/{repo}/releases/download/{tag}/nurb_{version}_x64-setup.exe"
    if url != expected_url:
        raise MinisignError(f"latest.json url {url!r} != expected asset {expected_url!r}")

    attached_sig = sig_path.read_text(encoding="utf-8").strip()
    if sig_field != attached_sig:
        raise MinisignError("latest.json signature differs from the release's .sig asset")

    installer = installer_path.read_bytes()
    sha256 = hashlib.sha256(installer).hexdigest()
    if expected_sha256 and sha256 != expected_sha256:
        raise MinisignError(f"SHA-256 {sha256} != expected {expected_sha256}")

    # latest.json carries the signature as the base64 of the minisign text,
    # the same envelope the .sig asset is. Unwrap it before parsing.
    try:
        sig_text = base64.b64decode(sig_field).decode("utf-8")
    except Exception as exc:
        raise MinisignError(f"latest.json signature is not base64 of minisign text: {exc}") from exc
    verify_minisign(pubkey_text, sig_text, installer)

    return {
        "tag": tag,
        "version": version,
        "repo": repo,
        "platform": platform,
        "pubkey_id": key_id.hex(),
        "signature_algorithm": alg.decode("ascii"),
        "installer_sha256": sha256,
        "installer_bytes": len(installer),
        "latest_json_version": meta.get("version"),
        "url": url,
        "verified": True,
        "notes": meta.get("notes"),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", required=True, help="release tag, e.g. v0.21.0")
    ap.add_argument("--repo", default="Alot1z/nurb-windows", help="owner/repo to verify")
    ap.add_argument(
        "--pubkey",
        default=None,
        help="committed updater pubkey (default: desktop/signing/tauri-updater.key.pub)",
    )
    ap.add_argument("--scratch", default=None, help="work directory for downloads")
    ap.add_argument("--offline", action="store_true", help="use files already in --scratch")
    ap.add_argument("--out", default=None, help="write the provenance dict as JSON here")
    args = ap.parse_args(argv)

    root = Path(__file__).resolve().parent.parent
    pubkey = Path(args.pubkey) if args.pubkey else root / "desktop" / "signing" / "tauri-updater.key.pub"
    scratch = Path(args.scratch) if args.scratch else Path(tempfile.mkdtemp(prefix="nurb-relverify-"))
    scratch.mkdir(parents=True, exist_ok=True)

    try:
        provenance = verify_release(args.tag, args.repo, pubkey, scratch, offline=args.offline)
    except (MinisignError, OSError, urllib.error.URLError) as exc:
        print(f"VERIFY FAILED: {exc}", flush=True)
        return 1

    print(
        f"VERIFIED {args.tag}: {provenance['installer_bytes']} bytes, "
        f"sha256 {provenance['installer_sha256']}, key {provenance['pubkey_id']}, "
        f"algorithm {provenance['signature_algorithm']}",
        flush=True,
    )
    if args.out:
        Path(args.out).write_text(json.dumps(provenance, indent=2), encoding="utf-8")
        print(f"provenance written to {args.out}", flush=True)
    if args.scratch is None:
        import shutil

        shutil.rmtree(scratch, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
