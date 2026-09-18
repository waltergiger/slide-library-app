import subprocess

import pytest

from app import folder_picker


def _result(code=0, out="", err=""):
    return subprocess.CompletedProcess([], code, out, err)


@pytest.fixture()
def fake_run(monkeypatch):
    calls = []

    def install(result):
        def run(cmd, **kw):
            calls.append(cmd)
            return result
        monkeypatch.setattr(folder_picker.subprocess, "run", run)
        return calls

    return install


def test_macos_uses_osascript_and_strips_trailing_slash(monkeypatch, fake_run):
    monkeypatch.setattr(folder_picker.sys, "platform", "darwin")
    calls = fake_run(_result(out="/Users/x/Slides/\n"))
    assert folder_picker.pick_folder() == "/Users/x/Slides"
    assert calls[0][0] == "osascript"


def test_macos_cancel_returns_none(monkeypatch, fake_run):
    monkeypatch.setattr(folder_picker.sys, "platform", "darwin")
    fake_run(_result(1, err="execution error: User canceled. (-128)"))
    assert folder_picker.pick_folder() is None


def test_macos_other_failure_is_unavailable(monkeypatch, fake_run):
    monkeypatch.setattr(folder_picker.sys, "platform", "darwin")
    fake_run(_result(1, err="some other error"))
    with pytest.raises(folder_picker.PickerUnavailable):
        folder_picker.pick_folder()


def test_root_path_keeps_its_slash(monkeypatch, fake_run):
    monkeypatch.setattr(folder_picker.sys, "platform", "darwin")
    fake_run(_result(out="/\n"))
    assert folder_picker.pick_folder() == "/"


def test_tk_child_process_cancel_and_missing_tkinter(monkeypatch, fake_run):
    monkeypatch.setattr(folder_picker.sys, "platform", "linux")
    calls = fake_run(_result(out="\n"))
    assert folder_picker.pick_folder() is None
    assert calls[0][0] == folder_picker.sys.executable  # never Tk in the server process

    fake_run(_result(3))
    with pytest.raises(folder_picker.PickerUnavailable, match="tkinter"):
        folder_picker.pick_folder()


def test_missing_binary_is_unavailable(monkeypatch):
    def run(cmd, **kw):
        raise FileNotFoundError("osascript")

    monkeypatch.setattr(folder_picker.sys, "platform", "darwin")
    monkeypatch.setattr(folder_picker.subprocess, "run", run)
    with pytest.raises(folder_picker.PickerUnavailable):
        folder_picker.pick_folder()
