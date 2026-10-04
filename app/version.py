"""The app version shown in the UI and served at /api/version.

GitHub release tags (vX.Y.Z) are the single authority. A git checkout derives
the version from the nearest tag, so the app can't disagree with GitHub; a ZIP
download has no .git, so it falls back to the VERSION file, which
scripts/release.sh writes in the same commit it tags.
"""
from __future__ import annotations

import re
import subprocess
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "VERSION"

_DESCRIBE = re.compile(r"^v(?P<version>\d+\.\d+\.\d+)(?:-(?P<ahead>\d+)-g(?P<commit>[0-9a-f]+))?(?P<dirty>-dirty)?$")


def parse_describe(text: str) -> dict | None:
    """Parses `git describe --tags --long --dirty` output, e.g. v0.4.1-2-g1a2b3c4-dirty."""
    m = _DESCRIBE.match(text.strip())
    if not m:
        return None
    return {
        "version": m["version"],
        "commits_ahead": int(m["ahead"] or 0),
        "commit": m["commit"],
        "dirty": bool(m["dirty"]),
        "source": "git",
    }


def file_version() -> str:
    try:
        text = VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return "0.0.0"
    return text if re.fullmatch(r"\d+\.\d+\.\d+", text) else "0.0.0"


def _git_describe() -> str | None:
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--long", "--dirty", "--match", "v[0-9]*"],
            cwd=ROOT, capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def build_info(describe: str | None, fallback: str) -> dict:
    info = parse_describe(describe) if describe else None
    if info is None:
        info = {"version": fallback, "commits_ahead": 0, "commit": None, "dirty": False, "source": "file"}
    # Exactly on a release tag shows as "0.4.1"; unreleased commits on top as "0.4.1+2", so a
    # dev build is never mistaken for the release.
    label = info["version"] + (f"+{info['commits_ahead']}" if info["commits_ahead"] else "")
    if info["dirty"]:
        label += " (modified)"
    cache_key = re.sub(r"[^0-9A-Za-z.+-]", "", label.replace(" (modified)", "-dirty"))
    return {**info, "label": label, "cache_key": cache_key}


@lru_cache(maxsize=1)
def get() -> dict:
    """Computed once per server start; restarting after a pull picks up the new version."""
    return build_info(_git_describe(), file_version())
