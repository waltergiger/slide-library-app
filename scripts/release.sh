#!/usr/bin/env bash
# Cuts a release so the app version and the GitHub tag can never disagree:
# tests -> VERSION file -> commit -> annotated tag vX.Y.Z -> push both.
#
#   scripts/release.sh 0.4.1 "Short summary of the release"
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

die() { echo "release: $*" >&2; exit 1; }

version="${1:-}"
summary="${2:-}"
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "usage: scripts/release.sh X.Y.Z [\"summary\"]"
[[ -z "$(git status --porcelain)" ]] || die "working tree not clean — commit or stash first"
git rev-parse -q --verify "refs/tags/v$version" >/dev/null && die "tag v$version already exists"

git fetch -q --tags origin
[[ "$(git rev-parse HEAD)" == "$(git rev-parse '@{u}')" ]] || die "local branch differs from origin — pull/push first"

latest="$(git describe --tags --abbrev=0 --match 'v[0-9]*' 2>/dev/null || echo v0.0.0)"
[[ "$(printf '%s\n%s\n' "${latest#v}" "$version" | sort -V | tail -1)" == "$version" && "${latest#v}" != "$version" ]] \
    || die "v$version is not newer than $latest"

PY=python3; [[ -x .venv/bin/python ]] && PY=.venv/bin/python
"$PY" -m pytest -q
if command -v node >/dev/null; then node --test tests/js/*.test.js >/dev/null; fi

echo "$version" > VERSION
git add VERSION
git commit -q -m "chore: release v$version"
git tag -a "v$version" -m "v$version${summary:+

$summary}"
git push -q origin HEAD "v$version"
echo "released v$version ($(git rev-parse --short HEAD)) — restart the app to show it"
