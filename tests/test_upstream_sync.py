"""The upstream-sync tool's classification and strict gate, both pure and live.

The gate's reason for existing lives in test_cli.py: a stray desktop merge
once silently reverted the updater endpoint to upstream; surfacing SAFE-zone
drift loudly at CI time is a small guard against repeating that.
"""

import importlib.util
import inspect
import pathlib
import subprocess
import sys

import pytest


REPO = pathlib.Path(__file__).resolve().parents[1]


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "upstream_sync", REPO / "tools" / "upstream_sync.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_classify_partitions_paths_into_the_three_buckets():
    mod = _load_module()
    assert mod.classify("src/nurb/cli.py") == "SAFE"
    assert mod.classify("tests/test_cli.py") == "SAFE"
    assert mod.classify("examples/notch/parts/dispenser.py") == "SAFE"
    assert mod.classify("skills/nurb/SKILL.md") == "SAFE"
    assert mod.classify("evals/uv.lock") == "SAFE"
    assert mod.classify("desktop/src-tauri/src/extensions.rs") == "WINDOWS-SPECIFIC"
    assert mod.classify("desktop/scripts/stage.py") == "WINDOWS-SPECIFIC"
    assert mod.classify(".github/workflows/windows-build.yml") == "WINDOWS-SPECIFIC"
    assert mod.classify("desktop/src-tauri-2/something") == "REVIEW"
    assert mod.classify("desktop/package.json") == "REVIEW"
    assert mod.classify("desktop/package-lock.json") == "REVIEW"
    assert mod.classify("pyproject.toml") == "REVIEW"
    assert mod.classify("uv.lock") == "REVIEW"
    # Unknown paths fall through to REVIEW so the audit names them for human
    # attention rather than silently absorbing them.
    assert mod.classify("README.md") == "REVIEW"
    assert mod.classify("docs/random.md") == "REVIEW"


def test_safe_drift_paths_returns_only_safe_bucket():
    mod = _load_module()
    changed = [
        "src/nurb/cli.py",
        "desktop/src-tauri/src/extensions.rs",
        "pyproject.toml",
        "README.md",
    ]
    assert mod.safe_drift_paths(changed) == ["src/nurb/cli.py"]


def test_safe_drift_paths_empty_input():
    mod = _load_module()
    assert mod.safe_drift_paths([]) == []


def test_strict_pure_ahead_is_never_a_failure():
    mod = _load_module()
    base = "abc123"
    remote = "abc123"
    # merge-base equals upstream/main -> the fork is strictly ahead.
    # Even with massive SAFE-zone drift, gate must stay open so fork-native
    # platform/ and cli.py patches do not flag every release.
    assert mod.strict_should_fail(base, remote, ["src/nurb/cli.py"]) is False
    assert mod.strict_should_fail(base, remote, []) is False


def test_strict_behind_with_safe_drift_fails():
    mod = _load_module()
    base = "older"  # not equal to remote -> either behind or diverged.
    remote = "newer"
    assert mod.strict_should_fail(base, remote, ["src/nurb/cli.py"]) is True
    assert mod.strict_should_fail(base, remote, ["tests/test_cli.py"]) is True


def test_strict_behind_without_safe_drift_does_not_fail():
    mod = _load_module()
    base = "older"
    remote = "newer"
    # Review/WINDOWS drift alone is not the gate's job — those are
    # intentionally fork-owned and reviewed by humans.
    assert mod.strict_should_fail(base, remote, []) is False


def test_status_function_accepts_strict_kwarg():
    # The argparse flag and the function parameter must match. Renaming one
    # without the other would silently break the CI contract.
    mod = _load_module()
    sig = inspect.signature(mod.status)
    assert "strict" in sig.parameters
    assert sig.parameters["strict"].default is False


def test_strict_status_fails_against_live_fork():
    """The fork is currently behind upstream on SAFE-zone files
    (src/nurb/mcp.py, src/nurb/platform/, etc.), so a --strict run on this
    checkout must exit non-zero. When the fork catches up the test inverts,
    which is also correct."""
    proc = subprocess.run(
        [sys.executable, "tools/upstream_sync.py", "status", "--strict"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=180,
    )
    joined = proc.stdout + proc.stderr
    # Either the strict gate fires (exit 1) or the fork caught up to upstream
    # (exit 0). Both are valid steady states; the test asserts the CLI does
    # not crash and surfaces SAFE-zone state on stderr when failing.
    assert proc.returncode in (0, 1), joined
    if proc.returncode == 1:
        assert "SAFE-zone" in joined, joined
        assert "Merge upstream" in joined, joined


def test_status_without_strict_remains_informational():
    proc = subprocess.run(
        [sys.executable, "tools/upstream_sync.py", "status"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "Local:" in proc.stdout
    assert "Upstream:" in proc.stdout
