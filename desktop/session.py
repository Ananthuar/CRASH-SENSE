"""
CrashSense — Session Module (Desktop)
======================================

Provides a simple in-memory session singleton to track the currently
authenticated user across all desktop screens without passing arguments.

Usage:
    from desktop import session

    # After login:
    session.set_user({"uid": "...", "email": "...", ...})

    # Read anywhere:
    user = session.get_user()
    print(user["display_name"])

    # On logout:
    session.clear_user()
"""

# ── Session State ────────────────────────────────────────────────
# This dict is the single source of truth for the logged-in user.
# None values indicate an unauthenticated / demo session.
_current_user: dict = {
    "uid":          None,
    "email":        None,
    "display_name": None,
    "role":         None,
    "id_token":     None,
    "joined":       None,
}


def set_user(data: dict) -> None:
    """
    Populate the session with an authenticated user's data.

    Args:
        data: Dict with any subset of the session keys.
              Unknown keys are stored as-is.
    """
    global _current_user
    _current_user = {
        "uid":          data.get("uid"),
        "email":        data.get("email"),
        "display_name": data.get("display_name"),
        "role":         data.get("role", "User"),
        "id_token":     data.get("id_token"),
        "joined":       data.get("joined"),
    }


def get_user() -> dict:
    """Return a copy of the current session dict."""
    return dict(_current_user)


def clear_user() -> None:
    """Reset the session to an unauthenticated state."""
    global _current_user
    _current_user = {
        "uid":          None,
        "email":        None,
        "display_name": None,
        "role":         None,
        "id_token":     None,
        "joined":       None,
    }


def is_authenticated() -> bool:
    """Return True if a real (non-demo) user is signed in."""
    return _current_user.get("uid") is not None


def get_initials() -> str:
    """
    Derive 2-letter initials from the logged-in user's display name or email.

    Returns 'GU' (Guest User) when no session is active.
    """
    name = _current_user.get("display_name") or _current_user.get("email") or ""
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    elif len(parts) == 1:
        return parts[0][:2].upper()
    return "GU"
