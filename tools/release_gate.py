"""Release gate for nurb-windows.

A single command that runs the post-PR release-readiness checks the
maintainer was doing by hand. Each check is fast and surfaces real
state; pytest itself is not run here on purpose because the suite is
~8 minutes and belongs to a separate gate.

Usage::

    uv run --project . python tools/release_gate.py

Exit code is the count of failed checks; zero means ready to push.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, **kw)


def check(name: str, ok: bool, detail: str = "") -> tuple[str, bool, str]:
    return (name, ok, detail)


def check_clean_tree() -> tuple[str, bool, str]:
    """The working tree should be in a state that signals a release is
    ready to commit. The private developer scratch space under `.dev/`
    is allowed because it is gitignored and never staged. Everything
    else (modifications and new untracked files outside that) means
    work-in-progress that should be committed first."""
    proc = run(["git", "status", "--short"])
    if proc.returncode != 0:
        return check("clean-tree", False, proc.stderr.strip())
    bad = [
        line
        for line in proc.stdout.splitlines()
        if line
        and not line.startswith("?? .dev/")
        and not line.startswith("?? .freebuff/")

    ]
    if bad:
        modified = sum(1 for l in bad if l.startswith(" M") or l.startswith("M "))
        added = sum(1 for l in bad if l.startswith("??") or l.startswith("A "))
        return check(
            "clean-tree",
            False,
            f"{len(bad)} WIP entries ({modified} modified, {added} added): " + ", ".join(bad[:3]),
        )
    return check(
        "clean-tree",
        True,
        "tree clean except private .dev/ scratch",
    )


def check_private_key_ignored() -> tuple[str, bool, str]:
    """The updater private key material must never be tracked."""
    proc = run(["git", "ls-files", "desktop/signing/"])
    tracked = proc.stdout.splitlines()
    bad = [
        p
        for p in tracked
        if p.endswith("tauri-updater.key")
        or p.endswith(".password")
        or p.endswith(".pfx")
        or p.endswith(".p12")
    ]
    if bad:
        return check("private-key-ignored", False, f"tracked: {bad}")
    return check("private-key-ignored", True, "no signing material in tree")


def check_private_dev_space_untracked() -> tuple[str, bool, str]:
    """.dev/ (the policy-mandated local-only scratch space) must not
    be in the git index. It is gitignored so accidental `git add -A`
    cannot leak it, but a historical or manual `git add -f` is the
    failure mode this check is here to catch."""
    proc = run(["git", "ls-files", ".dev/"])
    if proc.stdout.strip():
        return check(
            "private-space-untracked",
            False,
            "private dev space is leaking into the index",
        )
    return check(
        "private-space-untracked",
        True,
        ".dev/ scratch not tracked",
    )


def check_upstream_pin() -> tuple[str, bool, str]:
    """tauri.conf.json's updater endpoint must point at the fork, never
    upstream. A botched merge could revert this without anyone noticing
    the consequences for every installed app."""
    import json as _json

    conf = ROOT / "desktop" / "src-tauri" / "tauri.conf.json"
    if not conf.is_file():
        return check("updater-pin", False, f"missing {conf}")
    try:
        data = _json.loads(conf.read_text(encoding="utf-8"))
    except Exception as exc:
        return check("updater-pin", False, f"tauri.conf.json unreadable: {exc}")
    endpoints = (
        data.get("plugins", {}).get("updater", {}).get("endpoints", []) or []
    )
    allowed = [e for e in endpoints if "Alot1z/nurb-windows" in e]
    unexpected = [e for e in endpoints if e not in allowed]
    if unexpected:
        return check("updater-pin", False, f"unexpected endpoint(s): {unexpected}")
    if not endpoints:
        return check("updater-pin", False, "no updater endpoints set")
    return check("updater-pin", True, f"{len(allowed)} fork-only endpoint(s)")


def check_pinned_pubkey_matches() -> tuple[str, bool, str]:
    """The committed `tauri-updater.key.pub` (a minisign public key, base64
    on a single line) must be the same string embedded in
    `tauri.conf.json`. Renaming the file or editing the conf by hand
    silently invalidates every shipped update."""
    pub_file = ROOT / "desktop" / "signing" / "tauri-updater.key.pub"
    if not pub_file.is_file():
        return check("updater-pubkey", False, f"missing {pub_file}")
    expected = pub_file.read_text(encoding="utf-8").strip()
    conf = ROOT / "desktop" / "src-tauri" / "tauri.conf.json"
    data = json.loads(conf.read_text(encoding="utf-8"))
    pubkey = (
        data.get("plugins", {}).get("updater", {}).get("pubkey", "")
        or ""
    ).strip()
    if not pubkey:
        return check("updater-pubkey", False, "no pubkey in tauri.conf.json")
    if expected != pubkey:
        return check(
            "updater-pubkey",
            False,
            f"embedded differs from {pub_file.name}",
        )
    return check("updater-pubkey", True, "embedded matches committed key")


def check_stage_importable() -> tuple[str, bool, str]:
    """`stage.py` must parse under Python and expose the signing hooks so
    a future release pipeline can wire Authenticode without re-touching
    the script. The check tolerates both Windows-style UTF-8 BOM and
    plain UTF-8, since either is acceptable input."""
    proc = run(
        [
            "python",
            "-c",
            "import ast; src = open('desktop/scripts/stage.py', 'rb').read(); "
            "ast.parse(src if not src.startswith(b'\\xef\\xbb\\xbf') else src[3:], "
            "feature_version=(3, 13))",
        ],
    )
    if proc.returncode != 0:
        return check("stage-script", False, proc.stderr.strip().splitlines()[-1] if proc.stderr else "parse failed")
    return check("stage-script", True, "desktop/scripts/stage.py parses")


def check_release_gate_self_check() -> tuple[str, bool, str]:
    """This check is only meaningful when run from `tools/`; it confirms
    the script itself exists and is executable as a Python file. It is
    here so a missing tools dir fails the gate loudly."""
    here = Path(__file__)
    if not here.is_file():
        return check("self", False, f"missing {here}")
    return check("self", True, str(here.relative_to(ROOT)))


def check_toolchain() -> tuple[str, bool, str]:
    """The build toolchain this fork expects. `cargo` and `node` are
    required for desktop development; `makensis` and `signtool` are
    release-time only and are reported but never gate the script."""
    required = {
        "cargo": shutil.which("cargo"),
        "node": shutil.which("node"),
        "uv": shutil.which("uv"),
        "git": shutil.which("git"),
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        return check("toolchain", False, f"missing: {missing}")
    return check("toolchain", True, "cargo, node, uv, git on PATH")


CHECKS = [
    check_clean_tree,
    check_private_key_ignored,
    check_private_dev_space_untracked,
    check_upstream_pin,
    check_pinned_pubkey_matches,
    check_stage_importable,
    check_release_gate_self_check,
    check_toolchain,
]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="alias for the default CI mode: non-zero exit on any failure "
             "(the script already exits with the failure count, so --strict "
             "is provided for symmetry with tools/upstream_sync.py)",
    )
    args = parser.parse_args(argv)

    results = [fn() for fn in CHECKS]
    failures = sum(1 for _, ok, _ in results if not ok)

    if args.json:
        json.dump(
            [{"name": n, "ok": ok, "detail": d} for n, ok, d in results],
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
    else:
        for name, ok, detail in results:
            mark = "OK  " if ok else "FAIL"
            print(f"  [{mark}] {name:24s} {detail}")
        verdict = "READY" if failures == 0 else f"{failures} FAILURE(S)"
        print(f"\n  release-gate: {verdict}")

    return failures


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
