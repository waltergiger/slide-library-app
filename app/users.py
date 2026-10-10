"""Who a request belongs to.

Security: identity is the self-declared name each browser sends (Settings →
Your name). It attributes content and separates per-user favorites; it does
not authenticate — anyone can send any name. Put a real login in front of the
app before relying on it in a shared deployment.
"""
from __future__ import annotations

import os
import re
from urllib.parse import unquote

HEADER = "x-slidelib-user"
MAX_LEN = 80
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def clean_name(raw: str | None) -> str | None:
    """Decoded (browsers URI-encode it, header values must be Latin-1), control
    characters stripped, whitespace collapsed and length-capped, because it is
    stored and shown to other users."""
    if not raw:
        return None
    name = " ".join(_CONTROL.sub("", unquote(raw)).split())[:MAX_LEN]
    return name or None


def default_name() -> str:
    """The OS account's full name: what a fresh browser on this machine uses,
    and who pre-existing (pre per-user) favorites are migrated to."""
    try:
        import pwd  # POSIX only
        full = pwd.getpwuid(os.getuid()).pw_gecos.split(",")[0].strip()
        if full:
            return full
    except (ImportError, KeyError):
        pass
    import getpass
    return getpass.getuser()
