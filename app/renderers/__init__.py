"""Slide rendering: PowerPoint first, LibreOffice as the fallback (see manager)."""
from .base import Engine, RenderError
from .libreoffice import find_soffice
from .manager import convert_to_pdf, has_usable_engine, reset, status, usable_engines

__all__ = ["Engine", "RenderError", "convert_to_pdf", "find_soffice", "has_usable_engine", "reset", "status", "usable_engines"]
