"""The release verifier's semantics and its failure modes.

The updater contract has a happy path and a long tail of things that must
fail closed: wrong key, tampered artifact, corrupted signature, malformed
metadata, mismatched identity. These tests generate a throwaway keypair and
build a fake release layout in a tmp dir, then assert that `release_verify`
accepts exactly the well-formed case and rejects every corruption with a
one-line reason (the CLI's exit code, which is what CI gates on).

The real v0.21.0 release is exercised separately by the release workflow
itself (`python tools/release_verify.py --tag v0.21.0` after attachment),
which is the live proof; these tests pin the semantics so that proof cannot
silently stop being meaningful.
"""

import base64
import importlib.util
import json
import pathlib
import subprocess
import sys

import pytest


REPO = pathlib.Path(__file__).resolve().parents[1]
TOOLS = REPO / "tools"


def _load_module():
    spec = importlib.util.spec_from_file_location("release_verify", TOOLS / "release_verify.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rv = _load_module()


@pytest.fixture(scope="module")
def keypair():
    seed = bytes(range(32))  # deterministic fixture key, never a real secret
    _, pub = rv.ed25519_keypair(seed)
    return seed, pub


def make_sig_text(seed, data, key_id=b"\x65\x55\xc7\x2e\x6c\x85\xbe\x18"):
    """Build a prehashed minisign signature over `data` with a fake key id."""
    sig = rv.ed25519_sign(seed, hashlib_blake2b(data))
    alg = b"ED"  # prehashed, like tauri's updater signatures
    blob = base64.b64encode(alg + key_id + sig).decode("ascii")
    # The global signature covers the trusted comment's content only, i.e.
    # everything after the 17-character "trusted comment: " prefix.
    global_sig = rv.ed25519_sign(seed, sig + b"fixture")
    return (
        "untrusted comment: signature from tauri secret key\n"
        f"{blob}\n"
        "trusted comment: fixture\n"
        f"{base64.b64encode(global_sig).decode('ascii')}\n"
    )


def hashlib_blake2b(data):
    import hashlib

    return hashlib.blake2b(data, digest_size=64).digest()


def make_pubkey_text(pub, key_id=b"\x65\x55\xc7\x2e\x6c\x85\xbe\x18"):
    blob = base64.b64encode(b"Ed" + key_id + pub).decode("ascii")
    return f"untrusted comment: minisign public key: {key_id.hex()}\n{blob}\n"


def build_release(tmp_path, seed, pub, corrupt=None, meta_twist=None):
    """Lay out scratch/{latest.json, release.sig, installer.exe} for a fake tag."""
    data = b"MZ" + bytes(range(256)) * 16
    sig_text = make_sig_text(seed, data)
    pub_text = make_pubkey_text(pub)
    meta = {
        "version": "9.9.9",
        "notes": "fixture",
        "platforms": {
            "windows-x86_64-nsis": {
                "signature": base64.b64encode(sig_text.encode()).decode("ascii"),
                "url": "https://github.com/Alot1z/nurb-windows/releases/download/v9.9.9/nurb_9.9.9_x64-setup.exe",
            }
        },
    }
    if meta_twist:
        meta_twist(meta)
    (tmp_path / "installer.exe").write_bytes(data)
    (tmp_path / "release.sig").write_text(base64.b64encode(sig_text.encode()).decode("ascii"))
    (tmp_path / "latest.json").write_text(json.dumps(meta))
    (tmp_path / "pubkey.pub").write_text(base64.b64encode(pub_text.encode()).decode("ascii"))
    return data


def run_verify(tmp_path):
    return subprocess.run(
        [
            sys.executable,
            str(TOOLS / "release_verify.py"),
            "--tag",
            "v9.9.9",
            "--repo",
            "Alot1z/nurb-windows",
            "--pubkey",
            str(tmp_path / "pubkey.pub"),
            "--offline",
            "--scratch",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )


def test_well_formed_release_verifies(tmp_path, keypair):
    seed, pub = keypair
    build_release(tmp_path, seed, pub)
    proc = run_verify(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "VERIFIED" in proc.stdout


def test_verification_is_idempotent(tmp_path, keypair):
    """A repeated update check must not change the verdict."""
    seed, pub = keypair
    build_release(tmp_path, seed, pub)
    first = run_verify(tmp_path)
    second = run_verify(tmp_path)
    assert first.returncode == second.returncode == 0


def test_corrupted_installer_fails(tmp_path, keypair):
    seed, pub = keypair
    build_release(tmp_path, seed, pub)
    installer = tmp_path / "installer.exe"
    raw = bytearray(installer.read_bytes())
    raw[100] ^= 0xFF
    installer.write_bytes(bytes(raw))
    proc = run_verify(tmp_path)
    assert proc.returncode == 1
    assert "does not verify" in proc.stdout


def test_wrong_key_fails(tmp_path, keypair):
    """A signature made by any other key must be rejected."""
    seed, _ = keypair
    other_seed = bytes(range(32, 64))
    _, other_pub = rv.ed25519_keypair(other_seed)
    build_release(tmp_path, seed, other_pub)  # signed by seed, key claims other_pub
    proc = run_verify(tmp_path)
    assert proc.returncode == 1
    assert "does not verify" in proc.stdout


def test_tampered_signature_fails(tmp_path, keypair):
    seed, pub = keypair
    data = build_release(tmp_path, seed, pub)
    sig_text = make_sig_text(seed, data)
    tampered = sig_text[:50] + ("A" if sig_text[50] != "A" else "B") + sig_text[51:]
    sig_env = base64.b64encode(tampered.encode()).decode("ascii")
    (tmp_path / "release.sig").write_text(sig_env)
    (tmp_path / "latest.json").write_text(
        json.dumps(
            {
                "version": "9.9.9",
                "platforms": {
                    "windows-x86_64-nsis": {"signature": sig_env, "url": "https://github.com/Alot1z/nurb-windows/releases/download/v9.9.9/nurb_9.9.9_x64-setup.exe"}
                },
            }
        )
    )
    proc = run_verify(tmp_path)
    assert proc.returncode == 1


def test_key_id_mismatch_fails(tmp_path, keypair):
    seed, pub = keypair
    build_release(tmp_path, seed, pub)
    other_id = b"\x00" * 8
    pub_text = make_pubkey_text(pub, key_id=other_id)
    (tmp_path / "pubkey.pub").write_text(base64.b64encode(pub_text.encode()).decode("ascii"))
    proc = run_verify(tmp_path)
    assert proc.returncode == 1
    assert "key id mismatch" in proc.stdout


def test_malformed_latest_json_fails(tmp_path, keypair):
    seed, pub = keypair
    build_release(tmp_path, seed, pub)
    (tmp_path / "latest.json").write_text("{not json")
    proc = run_verify(tmp_path)
    assert proc.returncode == 1
    assert "malformed" in proc.stdout


def test_version_mismatch_fails(tmp_path, keypair):
    seed, pub = keypair
    build_release(tmp_path, seed, pub, meta_twist=lambda m: m.__setitem__("version", "1.0.0"))
    proc = run_verify(tmp_path)
    assert proc.returncode == 1
    assert "version" in proc.stdout


def test_url_mismatch_fails(tmp_path, keypair):
    seed, pub = keypair
    build_release(
        tmp_path,
        seed,
        pub,
        meta_twist=lambda m: m["platforms"]["windows-x86_64-nsis"].__setitem__(
            "url", "https://evil.example/nurb.exe"
        ),
    )
    proc = run_verify(tmp_path)
    assert proc.returncode == 1
    assert "url" in proc.stdout


def test_signature_field_differs_from_sig_asset_fails(tmp_path, keypair):
    seed, pub = keypair
    build_release(tmp_path, seed, pub)
    # Swap in a valid signature for different data: the field and the asset
    # agree with each other but not with the installer.
    other = b"other data"
    sig_env = base64.b64encode(make_sig_text(seed, other).encode()).decode("ascii")
    (tmp_path / "release.sig").write_text(sig_env)
    meta = json.loads((tmp_path / "latest.json").read_text())
    meta["platforms"]["windows-x86_64-nsis"]["signature"] = sig_env
    (tmp_path / "latest.json").write_text(json.dumps(meta))
    proc = run_verify(tmp_path)
    assert proc.returncode == 1
    assert "does not verify" in proc.stdout


def test_missing_offline_files_fail(tmp_path, keypair):
    seed, pub = keypair
    build_release(tmp_path, seed, pub)
    (tmp_path / "installer.exe").unlink()
    proc = run_verify(tmp_path)
    assert proc.returncode == 1


def test_committed_pubkey_envelope_decodes(tmp_path):
    """The real committed key must decode, so CI's verification is meaningful."""
    pubkey = REPO / "desktop" / "signing" / "tauri-updater.key.pub"
    text = rv.load_pubkey_envelope(pubkey)
    key_id, key, alg = rv.parse_public_key(text)
    assert len(key) == 32
    assert len(key_id) == 8
    assert alg in (b"Ed", b"ED")
    assert text.splitlines()[0].startswith("untrusted comment:")


def test_spaced_and_unicode_paths_still_verify(tmp_path, keypair):
    """A checkout under a path with spaces and non-ASCII characters must not
    break the verifier: the tool passes paths as arguments (never through a
    shell), and this guards that property against a future shell-string
    regression. Real installs live under paths like this."""
    seed, pub = keypair
    spaced = tmp_path / "space agent test" / "N\u00fcrb \u6d4b\u8bd5"
    spaced.mkdir(parents=True)
    build_release(spaced, seed, pub)
    proc = run_verify(spaced)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "VERIFIED" in proc.stdout
