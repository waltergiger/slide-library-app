import shutil
import subprocess

import pytest

from app import version


def test_parse_describe_variants():
    assert version.parse_describe("v0.4.1-0-g1a2b3c4") == {
        "version": "0.4.1", "commits_ahead": 0, "commit": "1a2b3c4", "dirty": False, "source": "git"}
    assert version.parse_describe("v0.4.1-3-gabcdef0-dirty")["commits_ahead"] == 3
    assert version.parse_describe("v0.4.1-3-gabcdef0-dirty")["dirty"] is True
    assert version.parse_describe("1a2b3c4") is None          # no tag reachable
    assert version.parse_describe("release-2") is None


def test_labels_distinguish_release_dev_and_modified_builds():
    assert version.build_info("v0.4.1-0-g1a2b3c4", "9.9.9")["label"] == "0.4.1"
    dev = version.build_info("v0.4.1-2-g1a2b3c4-dirty", "9.9.9")
    assert dev["label"] == "0.4.1+2 (modified)" and dev["cache_key"] == "0.4.1+2-dirty"


def test_zip_download_without_git_falls_back_to_version_file(tmp_path, monkeypatch):
    (tmp_path / "VERSION").write_text("1.2.3\n")
    monkeypatch.setattr(version, "VERSION_FILE", tmp_path / "VERSION")
    info = version.build_info(None, version.file_version())
    assert (info["label"], info["source"]) == ("1.2.3", "file")
    (tmp_path / "VERSION").write_text("<script>")
    assert version.file_version() == "0.0.0"                 # garbage never reaches the page


@pytest.mark.skipif(not shutil.which("git") or not (version.ROOT / ".git").exists(), reason="needs a git checkout")
def test_version_file_matches_latest_release_tag():
    # Guards against tagging on GitHub without the VERSION file (ZIP installs) following.
    r = subprocess.run(["git", "describe", "--tags", "--abbrev=0", "--match", "v[0-9]*"],
                       cwd=version.ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        pytest.skip("no release tags fetched")
    assert r.stdout.strip() == "v" + version.file_version()
