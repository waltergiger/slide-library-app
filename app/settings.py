"""User-configurable paths and filesystem persistence for saved Builder decks."""
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

from pptx import Presentation

from . import db

DEFAULT_DRAFTS_PATH = db.DATA_DIR / "drafts"
_DRAFTS_PATH_KEY = "drafts_path"
_TEMPLATE_PATH_KEY = "template_path"
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._ -]+")


def get() -> dict[str, str]:
    return {
        "template_path": db.get_setting(_TEMPLATE_PATH_KEY),
        "drafts_path": db.get_setting(_DRAFTS_PATH_KEY, str(DEFAULT_DRAFTS_PATH)),
    }


def validate_template_path(value: str) -> str:
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError("PowerPoint template path must be absolute")
    if path.suffix.lower() not in {".pptx", ".potx"}:
        raise ValueError("PowerPoint template must be a .pptx or .potx file")
    if not path.is_file():
        raise ValueError(f"PowerPoint template not found: {path}")
    try:
        Presentation(str(path))
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"PowerPoint template could not be opened: {path}") from exc
    return str(path)


def validate_drafts_path(value: str) -> str:
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError("Drafts folder must be an absolute path")
    if path.exists() and not path.is_dir():
        raise ValueError(f"Drafts path is not a folder: {path}")
    return str(path)


def update(template_path: str | None = None, drafts_path: str | None = None) -> dict[str, str]:
    current = get()
    if template_path is not None:
        template_path = template_path.strip()
        current["template_path"] = validate_template_path(template_path) if template_path else ""
    if drafts_path is not None:
        current["drafts_path"] = validate_drafts_path(drafts_path.strip())
    db.set_setting(_TEMPLATE_PATH_KEY, current["template_path"])
    db.set_setting(_DRAFTS_PATH_KEY, current["drafts_path"])
    return current


def persist_draft(draft: dict) -> None:
    folder = Path(get()["drafts_path"]).expanduser()
    folder.mkdir(parents=True, exist_ok=True)
    stem = _SAFE_NAME.sub("", draft["name"]).strip(" .") or "Untitled deck"
    path = folder / f"{stem}-{draft['id']}.json"
    for previous in folder.glob(f"*-{draft['id']}.json"):
        if previous != path:
            previous.unlink(missing_ok=True)
    payload = {
        "name": draft["name"],
        "category": draft["category"],
        "created_at": draft["created_at"],
        "updated_at": draft["updated_at"],
        **draft["content"],
    }
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass