"""Saved Builder decks: turns stored slide references back into display data.

A draft only stores which slides (file_id + slide_index) sit in which
chapter. Opening it re-resolves every reference against the live index, so
thumbnails and titles are always current, and a slide whose deck was removed
or shortened is flagged `missing` instead of breaking the Builder or export.
"""
from __future__ import annotations

from . import db


def resolve_slide(ref: dict) -> dict:
    file_row = db.get_file(ref["file_id"])
    slide_row = db.get_slide(ref["file_id"], ref["slide_index"]) if file_row else None
    if slide_row is None:
        return {
            "file_id": ref["file_id"],
            "slide_index": ref["slide_index"],
            "title": ref.get("title") or f"Slide {ref['slide_index'] + 1}",
            "deck_title": ref.get("deck_title") or "",
            "thumb_url": None,
            "missing": True,
        }
    return {
        "file_id": ref["file_id"],
        "slide_index": ref["slide_index"],
        "title": slide_row["title"],
        "deck_title": file_row["title"],
        "thumb_url": f"/api/thumb/{slide_row['thumb_file']}" if slide_row["thumb_file"] else None,
        "missing": False,
    }


def hydrate(draft: dict) -> dict:
    content = draft["content"]
    return {
        "id": draft["id"],
        "name": draft["name"],
        "add_dividers": content.get("add_dividers", True),
        "updated_at": draft["updated_at"],
        "chapters": [
            {"id": ch["id"], "name": ch["name"], "slides": [resolve_slide(s) for s in ch["slides"]]}
            for ch in content.get("chapters", [])
        ],
    }


def summarize(draft: dict) -> dict:
    chapters = draft["content"].get("chapters", [])
    return {
        "id": draft["id"],
        "name": draft["name"],
        "updated_at": draft["updated_at"],
        "chapter_count": len(chapters),
        "slide_count": sum(len(ch["slides"]) for ch in chapters),
    }
