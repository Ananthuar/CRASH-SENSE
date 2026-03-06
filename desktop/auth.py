"""
CrashSense — Auth Module (Desktop)
====================================

Primary auth: Email + Password via Firebase REST API (fully in-app).
Secondary:    Google OAuth via browser popup.

Includes email verification: after signup, Firebase sends a verification
email automatically. On login, we check the emailVerified flag.

Public API:
    sign_up_email_password(email, password) → user dict
    sign_in_email_password(email, password) → user dict
    send_verification_email(id_token)       → None (sends email)
    sign_in_with_google()                   → user dict  (opens browser)
    AuthError                               → raised on auth failures
"""

import os
import sys
import threading
import webbrowser
import datetime
import requests
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv

def get_asset_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # If running as a normal python script, use the project root
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base_path, relative_path)

_ENV_PATH = get_asset_path(".env")
load_dotenv(_ENV_PATH)

FIREBASE_WEB_API_KEY = os.getenv("FIREBASE_WEB_API_KEY", "")
FIREBASE_AUTH_BASE   = "https://identitytoolkit.googleapis.com/v1/accounts"
BACKEND_BASE         = "http://127.0.0.1:5000"


class AuthError(Exception):
    """Raised when an authentication call fails with a user-friendly message."""
    pass


# ─────────────────────────────────────────────────────────────────
#  Firebase Auth REST API helper
# ─────────────────────────────────────────────────────────────────

_ERROR_MESSAGES = {
    "EMAIL_NOT_FOUND":              "No account found with this email.",
    "INVALID_PASSWORD":             "Incorrect password. Please try again.",
    "USER_DISABLED":                "This account has been disabled.",
    "EMAIL_EXISTS":                 "An account with this email already exists.",
    "WEAK_PASSWORD":                "Password must be at least 6 characters.",
    "INVALID_EMAIL":                "Please enter a valid email address.",
    "TOO_MANY_ATTEMPTS_TRY_LATER":  "Too many failed attempts. Try again later.",
    "INVALID_LOGIN_CREDENTIALS":    "Incorrect email or password. Please try again.",
    "MISSING_PASSWORD":             "Please enter a password.",
}


def _firebase_auth_post(endpoint: str, payload: dict) -> dict:
    url = f"{FIREBASE_AUTH_BASE}:{endpoint}?key={FIREBASE_WEB_API_KEY}"
    try:
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
    except requests.exceptions.ConnectionError:
        raise AuthError("Cannot connect. Check your internet connection.")
    except requests.exceptions.Timeout:
        raise AuthError("Request timed out. Please try again.")
    except Exception as exc:
        msg = f"Unexpected error: {exc}"
        raise AuthError(msg)

    if not resp.ok:
        code = data.get("error", {}).get("message", "UNKNOWN_ERROR")
        raise AuthError(_ERROR_MESSAGES.get(code, f"Authentication failed: {code}"))

    return data


# ─────────────────────────────────────────────────────────────────
#  Profile helpers
# ─────────────────────────────────────────────────────────────────

def _fetch_profile(uid: str) -> dict | None:
    try:
        r = requests.get(f"{BACKEND_BASE}/api/users/{uid}/profile", timeout=3)
        return r.json() if r.ok else None
    except Exception:
        return None


def _ensure_profile(uid: str, display_name: str, email: str) -> dict:
    profile = _fetch_profile(uid)
    if not profile:
        payload = {
            "display_name": display_name,
            "email":        email,
            "role":         "User",
            "joined":       datetime.datetime.utcnow().strftime("%Y-%m-%d"),
        }
        try:
            requests.post(f"{BACKEND_BASE}/api/users/{uid}/profile",
                          json=payload, timeout=5)
        except Exception:
            pass
        return payload
    return profile


def _user_dict(uid: str, email: str, display_name: str, id_token: str) -> dict:
    profile = _fetch_profile(uid)
    if not profile:
        profile = _ensure_profile(uid, display_name, email)
    display_name = profile.get("display_name", display_name)
    return {
        "uid":          uid,
        "email":        email,
        "id_token":     id_token,
        "display_name": display_name,
        "role":         profile.get("role", "User"),
        "joined":       profile.get("joined", ""),
    }


# ─────────────────────────────────────────────────────────────────
#  Email Verification
# ─────────────────────────────────────────────────────────────────

def send_verification_email(id_token: str) -> None:
    """Ask Firebase to send a verification email to the user."""
    _firebase_auth_post("sendOobCode", {
        "requestType": "VERIFY_EMAIL",
        "idToken":     id_token,
    })


def is_email_verified(id_token: str) -> bool:
    """Check whether the user's email is verified."""
    data = _firebase_auth_post("lookup", {"idToken": id_token})
    users = data.get("users", [])
    if users:
        return users[0].get("emailVerified", False)
    return False


# ─────────────────────────────────────────────────────────────────
#  Email + Password Auth  (fully in-app, no browser)
# ─────────────────────────────────────────────────────────────────

def sign_up_email_password(email: str, password: str,
                           display_name: str = "") -> dict:
    """Create a new Firebase user with email + password.
    Automatically sends a verification email after account creation."""
    data = _firebase_auth_post("signUp", {
        "email":             email,
        "password":          password,
        "returnSecureToken": True,
    })
    uid      = data.get("localId", "")
    id_token = data.get("idToken", "")
    name     = display_name or email.split("@")[0]

    # Update display name in Firebase
    try:
        _firebase_auth_post("update", {
            "idToken":     id_token,
            "displayName": name,
        })
    except Exception:
        pass

    # Send verification email
    try:
        send_verification_email(id_token)
    except Exception:
        pass  # Don't block signup if verification email fails

    result = _user_dict(uid, email, name, id_token)
    result["email_verified"] = False  # Just created, not yet verified
    return result


def sign_in_email_password(email: str, password: str) -> dict:
    """Sign in an existing Firebase user with email + password."""
    data = _firebase_auth_post("signInWithPassword", {
        "email":             email,
        "password":          password,
        "returnSecureToken": True,
    })
    uid      = data.get("localId", "")
    id_token = data.get("idToken", "")
    name     = data.get("displayName") or email.split("@")[0]
    result   = _user_dict(uid, email, name, id_token)

    # Check email verification status
    try:
        is_verified = is_email_verified(id_token)
        result["email_verified"] = is_verified
    except Exception:
        is_verified = False
        result["email_verified"] = False

    if not is_verified:
        raise AuthError("Please verify your email address before signing in.")

    return result


# ─────────────────────────────────────────────────────────────────
#  Google OAuth  (browser popup — required by OAuth protocol)
# ─────────────────────────────────────────────────────────────────

_CALLBACK_PORT = 5557


class _ReuseAddrServer(HTTPServer):
    allow_reuse_address = True


def sign_in_with_google() -> dict:
    """Open browser for Google OAuth. Returns user dict once complete."""
    result: dict = {}
    done = threading.Event()

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            params = parse_qs(urlparse(self.path).query)
            if "error" in params:
                result["error"] = params["error"][0]
            else:
                for key in ("uid", "id_token", "email", "display_name"):
                    result[key] = params.get(key, [""])[0]

            body = b"""
            <html><head><title>CrashSense</title>
            <style>body{background:#0a0a0a;color:#fff;font-family:sans-serif;
            display:flex;align-items:center;justify-content:center;
            height:100vh;margin:0;}h2{color:#f97316;}</style></head>
            <body><div style="text-align:center">
            <h2>&#10003; Authentication Successful</h2>
            <p style="color:#b0b8c4">You can close this tab and return to CrashSense.</p>
            </div></body></html>"""
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            done.set()

        def log_message(self, *_):
            pass

    server = _ReuseAddrServer(("localhost", _CALLBACK_PORT), _Handler)
    t = threading.Thread(target=server.handle_request, daemon=True)
    t.start()

    callback_url = f"http://localhost:{_CALLBACK_PORT}"
    webbrowser.open(f"{BACKEND_BASE}/auth/google?callback={callback_url}")

    if not done.wait(timeout=300):
        server.server_close()
        raise AuthError("Timed out waiting for Google sign-in.")

    server.server_close()

    if "error" in result:
        raise AuthError(f"Google sign-in failed: {result['error']}")

    uid   = result.get("uid", "")
    email = result.get("email", "")
    name  = result.get("display_name") or email.split("@")[0]
    user  = _user_dict(uid, email, name, result.get("id_token", ""))
    user["email_verified"] = True  # Google accounts are always verified
    return user
